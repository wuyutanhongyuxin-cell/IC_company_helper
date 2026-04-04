"""工单路由 — Phase 1 占位，Step 5 完整实现"""
from app.blueprints.work_order import work_order_bp


@work_order_bp.route('/')
def list_orders():
    """工单列表 — 占位"""
    return '<h1>Work Orders — TODO</h1>'
