"""
工单状态路由 — 状态推进 / 异常恢复 / 检验数据
从 routes.py 拆分，保持单文件 < 200 行
"""
from datetime import datetime, timezone

from flask import redirect, url_for, flash, request, render_template, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _

from app.blueprints.work_order import work_order_bp
from app.extensions import db
from app.models.work_order import WorkOrder, WorkOrderStatusLog
from app.models.audit_log import log_action
from app.forms.work_order import InspectionForm, StatusForm
from app.utils.state_machine import (
    STATUS_LABELS, can_transition, get_resume_target,
)


@work_order_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def change_status(id):
    """推进状态 / 进入异常挂起"""
    order = db.get_or_404(WorkOrder, id)
    form = StatusForm()
    if not form.validate():
        flash(_('请求无效，请刷新页面重试'), 'danger')
        return redirect(url_for('work_order.detail_order', id=id))

    target = request.form.get('target_status', '').strip()

    if not can_transition(order.status, target):
        flash(_('不允许从 %(f)s 转换到 %(t)s',
                f=STATUS_LABELS.get(order.status),
                t=STATUS_LABELS.get(target, _('未知状态'))), 'danger')
        return redirect(url_for('work_order.detail_order', id=id))

    # 推进到 completed 前必须已填写检验数据
    if target == 'completed' and not order.inspection_result:
        flash(_('请先填写检验数据再完成工单'), 'warning')
        return redirect(url_for('work_order.detail_order', id=id))

    _record_transition(order, target, form.notes.data)

    if target == 'exception_hold':
        order.previous_status = order.status
    order.status = target
    if target == 'completed':
        order.completed_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('状态推进失败')
        flash(_('状态更新失败，请重试'), 'danger')
    else:
        flash(_('状态已更新为 %(s)s', s=STATUS_LABELS.get(target, target)), 'success')
    return redirect(url_for('work_order.detail_order', id=id))


@work_order_bp.route('/<int:id>/resume', methods=['POST'])
@login_required
def resume_order(id):
    """从异常挂起恢复"""
    order = db.get_or_404(WorkOrder, id)
    if order.status != 'exception_hold':
        flash(_('仅异常挂起状态可恢复'), 'warning')
        return redirect(url_for('work_order.detail_order', id=id))

    target = get_resume_target(order.previous_status)
    if not target:
        flash(_('无法确定恢复目标状态'), 'danger')
        return redirect(url_for('work_order.detail_order', id=id))

    form = StatusForm()
    if not form.validate():
        flash(_('请求无效，请刷新页面重试'), 'danger')
        return redirect(url_for('work_order.detail_order', id=id))

    _record_transition(order, target, form.notes.data)
    order.status = target
    order.previous_status = None

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('异常恢复失败')
        flash(_('恢复失败，请重试'), 'danger')
    else:
        flash(_('已恢复到 %(s)s', s=STATUS_LABELS.get(target, target)), 'success')
    return redirect(url_for('work_order.detail_order', id=id))


@work_order_bp.route('/<int:id>/inspection', methods=['GET', 'POST'])
@login_required
def inspection(id):
    """填写检验数据 — 仅 inspection 状态"""
    order = db.get_or_404(WorkOrder, id)
    if order.status != 'inspection':
        flash(_('仅检验状态可填写检验数据'), 'warning')
        return redirect(url_for('work_order.detail_order', id=id))

    form = InspectionForm(obj=order)
    if form.validate_on_submit():
        order.yield_rate = form.yield_rate.data
        order.max_chipping_actual = form.max_chipping_actual.data
        order.inspection_result = form.inspection_result.data
        order.inspection_notes = form.inspection_notes.data
        log_action(current_user.id, 'update', 'work_order', order.id,
                   details={'inspection_result': order.inspection_result})
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('检验数据保存失败')
            flash(_('保存失败，请重试'), 'danger')
            return render_template('work_order/inspection.html',
                                   form=form, order=order)
        flash(_('检验数据已保存'), 'success')
        return redirect(url_for('work_order.detail_order', id=id))

    return render_template('work_order/inspection.html', form=form, order=order)


# ---- 私有辅助函数 ----

def _record_transition(order, target, notes=None):
    """记录状态变更日志 + 审计日志"""
    log = WorkOrderStatusLog(
        work_order_id=order.id,
        from_status=order.status,
        to_status=target,
        operator_id=current_user.id,
        notes=notes,
    )
    db.session.add(log)
    log_action(current_user.id, 'status_change', 'work_order', order.id,
               details={'from': order.status, 'to': target})
