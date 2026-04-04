"""
Recipe 模型 — 切割参数库（版本化单表设计）
recipe_group_id 分组 + version 自增
工单通过 recipes.id (PK) 绑定不可变版本
"""
from datetime import datetime, timezone

from app.extensions import db


class Recipe(db.Model):
    """切割参数配方表 — 版本化单表设计"""
    __tablename__ = 'recipes'
    __table_args__ = (
        db.UniqueConstraint('recipe_group_id', 'version', name='uq_recipe_group_version'),
        db.Index('ix_recipe_material_size', 'wafer_material', 'wafer_size'),
    )

    id = db.Column(db.Integer, primary_key=True)
    recipe_group_id = db.Column(db.Integer, nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    # 切割参数
    wafer_material = db.Column(db.String(64), nullable=False)   # 材料类型
    wafer_size = db.Column(db.String(32), nullable=False)       # 晶圆尺寸
    thickness = db.Column(db.Float, nullable=False)             # 厚度(um)
    blade_model = db.Column(db.String(64), nullable=False)      # 刀片型号
    spindle_speed = db.Column(db.Integer, nullable=False)       # 主轴转速(RPM)
    feed_rate = db.Column(db.Float, nullable=False)             # 进给速度(mm/s)
    cut_depth = db.Column(db.Float, nullable=False)             # 切割深度(um)
    coolant_flow = db.Column(db.Float, nullable=False)          # 冷却水流量(L/min)
    max_chipping = db.Column(db.Float, nullable=False)          # 最大允许崩边(um)

    notes = db.Column(db.Text, nullable=True)                   # 备注
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # 最新版本=True

    # 关联
    # nullable=True: 允许系统初始化时创建无作者的种子数据
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # 关系
    creator = db.relationship('User', backref='recipes', lazy='select')

    def __repr__(self):
        return f'<Recipe group={self.recipe_group_id} v{self.version}>'
