"""
工单路由 — CRUD (创建/查看/编辑/列表)
所有已登录用户可操作
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from flask import abort
from sqlalchemy.orm import joinedload, subqueryload

from app.blueprints.work_order import work_order_bp
from app.extensions import db
from app.models.work_order import WorkOrder, WorkOrderStatusLog
from app.models.recipe import Recipe
from app.models.audit_log import log_action
from app.forms.work_order import WorkOrderForm, StatusForm
from app.utils.helpers import generate_order_number
from app.utils.state_machine import (
    STATUS_LABELS, STATUS_COLORS, STATUS_ORDER,
    get_next_status, get_resume_target,
)


@work_order_bp.route('/')
@login_required
def list_orders():
    """工单列表 — 分页 + 状态筛选 + 工单号/客户搜索"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)

    query = db.select(WorkOrder).options(
        joinedload(WorkOrder.operator), joinedload(WorkOrder.recipe)
    )

    status = request.args.get('status', '').strip()
    if status:
        query = query.filter(WorkOrder.status == status)

    search = request.args.get('q', '').strip()
    if search:
        like = f'%{search}%'
        query = query.filter(
            WorkOrder.order_number.like(like) | WorkOrder.customer.like(like)
        )

    query = query.order_by(WorkOrder.created_at.desc())
    pagination = db.paginate(query, page=page, per_page=per_page)

    return render_template(
        'work_order/list.html', pagination=pagination,
        current_status=status, current_search=search,
        status_labels=STATUS_LABELS, status_colors=STATUS_COLORS,
        all_statuses=STATUS_ORDER + ['exception_hold'],
    )


@work_order_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_order():
    """创建工单"""
    form = WorkOrderForm()
    form.recipe_id.choices = _get_recipe_choices()

    if form.validate_on_submit():
        order = WorkOrder(
            order_number=generate_order_number(),
            customer=form.customer.data,
            wafer_spec=form.wafer_spec.data,
            quantity=form.quantity.data,
            recipe_id=form.recipe_id.data,
            operator_id=current_user.id,
        )
        db.session.add(order)
        db.session.flush()
        log_action(current_user.id, 'create', 'work_order', order.id,
                   details={'order_number': order.order_number})
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('工单创建失败')
            flash(_('保存失败，请重试'), 'danger')
            return render_template('work_order/form.html', form=form, is_edit=False)
        flash(_('工单 %(num)s 创建成功', num=order.order_number), 'success')
        return redirect(url_for('work_order.detail_order', id=order.id))

    return render_template('work_order/form.html', form=form, is_edit=False)


@work_order_bp.route('/<int:id>')
@login_required
def detail_order(id):
    """工单详情 — 含状态时间线和操作按钮"""
    # 预加载 status_logs + operator 避免 N+1 查询
    order = db.session.execute(
        db.select(WorkOrder).filter_by(id=id).options(
            joinedload(WorkOrder.recipe),
            joinedload(WorkOrder.operator),
            subqueryload(WorkOrder.status_logs).joinedload(WorkOrderStatusLog.operator),
        )
    ).scalar_one_or_none()
    if order is None:
        abort(404)

    next_status = get_next_status(order.status)
    resume_target = None
    if order.status == 'exception_hold' and order.previous_status:
        resume_target = get_resume_target(order.previous_status)
    # 是否可进入异常挂起（非完成、非已挂起的线性状态）
    can_hold = order.status in STATUS_ORDER[:-1]

    return render_template(
        'work_order/detail.html', order=order,
        next_status=next_status, resume_target=resume_target,
        can_hold=can_hold,
        status_labels=STATUS_LABELS, status_colors=STATUS_COLORS,
        status_form=StatusForm(),
    )


@work_order_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_order(id):
    """编辑工单 — 仅 incoming 状态可编辑"""
    order = db.get_or_404(WorkOrder, id)
    if order.status != 'incoming':
        flash(_('仅来料状态的工单可编辑'), 'warning')
        return redirect(url_for('work_order.detail_order', id=id))

    form = WorkOrderForm(obj=order)
    form.recipe_id.choices = _get_recipe_choices()

    if form.validate_on_submit():
        order.customer = form.customer.data
        order.wafer_spec = form.wafer_spec.data
        order.quantity = form.quantity.data
        order.recipe_id = form.recipe_id.data
        db.session.flush()
        log_action(current_user.id, 'update', 'work_order', order.id)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('工单编辑失败')
            flash(_('保存失败，请重试'), 'danger')
            return render_template('work_order/form.html', form=form,
                                   order=order, is_edit=True)
        flash(_('工单信息已更新'), 'success')
        return redirect(url_for('work_order.detail_order', id=id))

    return render_template('work_order/form.html', form=form,
                           order=order, is_edit=True)


# ---- 私有辅助函数 ----

def _get_recipe_choices():
    """获取当前活跃配方列表作为 SelectField choices"""
    recipes = db.session.execute(
        db.select(Recipe).filter_by(is_active=True)
        .order_by(Recipe.wafer_material, Recipe.wafer_size)
    ).scalars().all()
    return [(r.id, f'{r.wafer_material} / {r.wafer_size} v{r.version}') for r in recipes]
