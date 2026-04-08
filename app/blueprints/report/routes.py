"""
报告路由 — PDF 交付报告生成与预览
仅已完成(completed)的工单可生成报告
"""
from flask import (
    render_template, abort, make_response,
    request, current_app,
)
from flask_login import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy.orm import joinedload, subqueryload

from app.blueprints.report import report_bp
from app.extensions import db
from app.models.work_order import WorkOrder, WorkOrderStatusLog
from app.models.audit_log import log_action
from app.utils.state_machine import STATUS_LABELS


def _load_completed_order(order_id):
    """
    加载已完成的工单（含 recipe / operator / status_logs 关联）。
    未找到返回 404，未完成返回 400。
    """
    order = db.session.execute(
        db.select(WorkOrder).filter_by(id=order_id).options(
            joinedload(WorkOrder.recipe),
            joinedload(WorkOrder.operator),
            subqueryload(WorkOrder.status_logs)
            .joinedload(WorkOrderStatusLog.operator),
        )
    ).scalar_one_or_none()

    if order is None:
        abort(404)
    if order.status != 'completed':
        abort(400, description=_('仅完成状态的工单可生成报告'))
    return order


def _render_report_html(order):
    """渲染交付报告 HTML（PDF 和预览共用）"""
    return render_template(
        'report/delivery_report.html',
        order=order,
        status_labels=STATUS_LABELS,
    )


@report_bp.route('/delivery/<int:order_id>')
@login_required
def delivery_report(order_id):
    """生成 PDF 交付报告并下载"""
    order = _load_completed_order(order_id)
    html_content = _render_report_html(order)

    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        # base_url 让 WeasyPrint 能解析相对路径（如 logo 图片）
        pdf_bytes = HTML(
            string=html_content,
            base_url=request.host_url,
        ).write_pdf(font_config=font_config)
    except ImportError:
        current_app.logger.error('WeasyPrint 未安装，无法生成 PDF')
        abort(500, description=_('PDF 组件未安装，请联系管理员'))
    except Exception:
        current_app.logger.exception('PDF 生成失败: 工单 %s', order.order_number)
        abort(500, description=_('PDF 生成失败，请联系管理员'))

    # 审计日志（与 PDF 生成分离，避免审计失败影响下载）
    log_action(current_user.id, 'export', 'work_order', order.id,
               details={'format': 'pdf'})
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.warning('PDF 审计日志保存失败')

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    filename = f'{order.order_number}.pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@report_bp.route('/delivery/<int:order_id>/preview')
@login_required
def delivery_report_preview(order_id):
    """HTML 预览交付报告（与 PDF 同内容，方便浏览器查看）"""
    order = _load_completed_order(order_id)
    return _render_report_html(order)
