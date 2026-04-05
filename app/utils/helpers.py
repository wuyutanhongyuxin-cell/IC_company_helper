"""
工具函数 — 工单号生成、日期计算等
"""
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models.work_order import WorkOrder


def generate_order_number():
    """
    生成工单号: WO-YYYYMMDD-XXXX

    日期使用服务器本地时间（工厂部署在本地局域网，服务器时区即工厂时区）。
    同日序号自增。并发安全由 UNIQUE 约束兜底（极端情况下 commit 失败触发重试）。
    """
    today = datetime.now().strftime('%Y%m%d')
    prefix = f'WO-{today}-'

    last = db.session.execute(
        db.select(func.max(WorkOrder.order_number))
        .filter(WorkOrder.order_number.like(f'{prefix}%'))
    ).scalar()

    seq = 1
    if last:
        try:
            seq = int(last.split('-')[-1]) + 1
        except (ValueError, IndexError):
            current_app.logger.warning('工单号格式异常: %s，序号从 1 重新计算', last)
            seq = 1

    return f'{prefix}{seq:04d}'


def get_today_start_utc_naive():
    """
    获取本地今日 00:00 对应的 UTC naive datetime。

    completed_at 等字段以 UTC(naive) 存储在 SQLite 中，
    用此函数生成的时间戳做 >= 比较，可正确筛选"本地今天"的记录。
    """
    utc_now = datetime.now(timezone.utc)
    local_now = utc_now.astimezone()                                    # 系统本地时区
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc).replace(tzinfo=None)
