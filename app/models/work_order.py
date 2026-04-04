"""
WorkOrder + WorkOrderStatusLog 模型
工单管理与状态流转记录
"""
from datetime import datetime, timezone

from app.extensions import db


class WorkOrder(db.Model):
    """工单表"""
    __tablename__ = 'work_orders'

    id = db.Column(db.Integer, primary_key=True)
    # 格式: WO-YYYYMMDD-XXXX (17 字符)，预留 32 字符以防未来扩展
    order_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    customer = db.Column(db.String(128), nullable=False)
    wafer_spec = db.Column(db.String(256), nullable=False)      # 晶圆规格
    quantity = db.Column(db.Integer, nullable=False)             # 片数

    # 绑定到具体版本的配方（通过 PK，不是 group_id）
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)

    # 状态
    status = db.Column(db.String(32), nullable=False, default='incoming')
    previous_status = db.Column(db.String(32), nullable=True)   # 异常挂起时保存

    # 操作员（可后续分配，ondelete=SET NULL 保留工单数据）
    operator_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

    # 检验数据
    yield_rate = db.Column(db.Float, nullable=True)             # 良率(%)
    max_chipping_actual = db.Column(db.Float, nullable=True)    # 崩边实测(um)
    inspection_result = db.Column(db.String(16), nullable=True)  # pass/fail
    inspection_notes = db.Column(db.Text, nullable=True)

    # 时间戳
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    # 关系
    recipe = db.relationship('Recipe', backref='work_orders', lazy='select')
    operator = db.relationship('User', backref='work_orders', lazy='select')
    # lazy='select' 替代已废弃的 'dynamic'（SQLAlchemy 2.x）
    # 排序需在查询时通过 db.select().order_by() 实现
    status_logs = db.relationship(
        'WorkOrderStatusLog', backref='work_order',
        lazy='select', order_by='WorkOrderStatusLog.created_at'
    )

    def __repr__(self):
        return f'<WorkOrder {self.order_number}>'


class WorkOrderStatusLog(db.Model):
    """工单状态变更日志"""
    __tablename__ = 'work_order_status_logs'

    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(
        db.Integer, db.ForeignKey('work_orders.id'), nullable=False
    )
    from_status = db.Column(db.String(32), nullable=False)
    to_status = db.Column(db.String(32), nullable=False)
    # ondelete=RESTRICT: 不允许删除有状态变更记录的用户（审计完整性）
    operator_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # 关系
    operator = db.relationship('User', lazy='select')

    def __repr__(self):
        return f'<StatusLog {self.from_status} → {self.to_status}>'
