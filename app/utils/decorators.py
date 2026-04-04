"""
权限装饰器 — 基于角色的访问控制
内置 login_required，未登录用户自动重定向到登录页
"""
from functools import wraps

from flask import abort
from flask_login import login_required, current_user


def role_required(*roles):
    """
    角色权限装饰器（已内置 login_required）

    用法: @role_required('admin')  — 无需额外加 @login_required
    未登录 → 重定向登录页，角色不匹配 → 403

    Args:
        roles: 允许的角色名列表，如 'admin', 'operator'
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator
