"""报告蓝图 — PDF 交付报告生成"""
from flask import Blueprint

report_bp = Blueprint('report', __name__, url_prefix='/reports')

from app.blueprints.report import routes  # noqa: E402, F401
