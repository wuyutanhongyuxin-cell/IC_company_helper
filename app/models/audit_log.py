"""
AuditLog 模型 — 操作审计日志
记录所有关键操作：创建/修改/删除/登录/状态变更
"""
import json
from datetime import datetime, timezone

from app.extensions import db


class AuditLog(db.Model):
    """审计日志表"""
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index('ix_audit_target', 'target_type', 'target_id'),
        db.Index('ix_audit_user', 'user_id'),
        db.Index('ix_audit_created', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # ondelete=SET NULL: 删除用户后保留审计日志，用户字段置空
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(64), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)     # JSON 格式变更详情
    created_at = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # 关系
    user = db.relationship('User', lazy='select')

    def set_details(self, data):
        """将 dict 序列化为 JSON 存储"""
        self.details = json.dumps(data, ensure_ascii=False)

    def get_details(self):
        """将 JSON 反序列化为 dict"""
        if self.details:
            try:
                return json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def __repr__(self):
        return f'<AuditLog {self.action} {self.target_type}:{self.target_id}>'


def log_action(user_id, action, target_type, target_id=None, details=None):
    """
    记录审计日志的便捷函数

    注意: 本函数只执行 db.session.add()，不 commit。
    调用方负责 db.session.commit()，这样审计日志与业务操作在同一事务中，
    业务失败时审计日志也会一起回滚（保证一致性）。

    Args:
        user_id: 操作用户 ID（系统操作为 None）
        action: 操作类型 (create/update/delete/login/status_change)
        target_type: 目标类型 (work_order/recipe/user)
        target_id: 目标 ID
        details: 变更详情 dict
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
    )
    if details:
        log.set_details(details)
    db.session.add(log)
