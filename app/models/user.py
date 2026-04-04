"""
User 模型 — 用户认证与权限
包含密码哈希、角色(admin/operator)、软禁用
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    # 256 字符: werkzeug scrypt 哈希恒定 163 字符，预留充足空间
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(16), nullable=False, default='operator')
    # 注意: 此 Column 有意覆盖 UserMixin.is_active 属性
    # Flask-Login 读取此字段判断账号是否启用，支持软禁用功能
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """是否为管理员"""
        return self.role == 'admin'

    def get_id(self):
        """Flask-Login 要求的方法"""
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username}>'
