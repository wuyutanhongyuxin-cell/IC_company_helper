"""工单蓝图 — 工单 CRUD + 状态流转"""
from flask import Blueprint

work_order_bp = Blueprint('work_order', __name__, url_prefix='/orders')

from app.blueprints.work_order import routes  # noqa: E402, F401
