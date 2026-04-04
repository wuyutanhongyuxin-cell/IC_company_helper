"""
权限装饰器 — 基于角色的访问控制
配合 @login_required 使用，限制特定角色访问
"""
from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    """
    角色权限装饰器

    用法: @login_required + @role_required('admin')
    未登录返回 401，角色不匹配返回 403

    Args:
        roles: 允许的角色名列表，如 'admin', 'operator'
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
