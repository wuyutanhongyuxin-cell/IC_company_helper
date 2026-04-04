"""报告路由 — Phase 1 占位，Step 7 完整实现"""
from app.blueprints.report import report_bp


@report_bp.route('/delivery/<int:order_id>')
def delivery_report(order_id):
    """PDF 交付报告 — 占位"""
    return f'<h1>Delivery Report #{order_id} — TODO</h1>'
