"""认证路由 — Phase 1 占位，Step 3 完整实现"""
from app.blueprints.auth import auth_bp


@auth_bp.route('/login')
def login():
    """登录页 — 占位"""
    return '<h1>Login — TODO</h1>'
