"""工单路由 — Phase 1 占位，Step 5 完整实现"""
from flask_login import login_required

from app.blueprints.work_order import work_order_bp


@work_order_bp.route('/')
@login_required
def list_orders():
    """工单列表 — 占位，Step 5 完整实现"""
    return '<h1>Work Orders — TODO Step 5</h1>'
