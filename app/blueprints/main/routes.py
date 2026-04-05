"""主页路由 — 仪表盘 + 语言切换"""
from datetime import datetime, time, timezone
from urllib.parse import urlparse

from flask import redirect, url_for, session, current_app, request, render_template
from flask_babel import gettext as _
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.blueprints.main import main_bp
from app.extensions import db
from app.models.work_order import WorkOrder
from app.utils.state_machine import STATUS_LABELS, STATUS_COLORS


@main_bp.route('/')
@login_required
def dashboard():
    """仪表盘 — 统计卡片 + 最近工单列表"""
    # ---- 统计数据 ----
    total = db.session.execute(
        db.select(func.count(WorkOrder.id))
    ).scalar() or 0

    # 在制 = 正在制造的工单（显式排除 completed 和 exception_hold）
    in_progress = db.session.execute(
        db.select(func.count(WorkOrder.id))
        .filter(WorkOrder.status.not_in(['completed', 'exception_hold']))
    ).scalar() or 0

    exception_count = db.session.execute(
        db.select(func.count(WorkOrder.id))
        .filter(WorkOrder.status == 'exception_hold')
    ).scalar() or 0

    # 今日完成: completed_at 以 UTC(naive) 存储，
    # 将本地今日 00:00 转为 UTC(naive) 进行比较
    _utc = datetime.now(timezone.utc)
    _local = _utc.astimezone()                           # 系统本地时区
    _midnight = _local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = _midnight.astimezone(timezone.utc).replace(tzinfo=None)

    today_completed = db.session.execute(
        db.select(func.count(WorkOrder.id))
        .filter(
            WorkOrder.status == 'completed',
            WorkOrder.completed_at >= today_start
        )
    ).scalar() or 0

    # ---- 最近 10 条工单 ----
    recent_orders = db.session.execute(
        db.select(WorkOrder)
        .options(joinedload(WorkOrder.operator))
        .order_by(WorkOrder.created_at.desc())
        .limit(10)
    ).scalars().all()

    return render_template(
        'main/dashboard.html',
        total=total,
        in_progress=in_progress,
        exception_count=exception_count,
        today_completed=today_completed,
        recent_orders=recent_orders,
        status_labels=STATUS_LABELS,
        status_colors=STATUS_COLORS,
    )


@main_bp.route('/set-language/<lang>')
def set_language(lang):
    """切换界面语言，存入 session，返回用户来源页"""
    supported = current_app.config.get('BABEL_SUPPORTED_LOCALES', ['zh'])
    if lang in supported:
        session['language'] = lang
    # 防止 open redirect: 只允许同源 referrer
    referrer = request.referrer
    if referrer:
        parsed = urlparse(referrer)
        if parsed.netloc and parsed.netloc != request.host:
            referrer = None
    return redirect(referrer or url_for('main.dashboard'))
