"""主页路由 — Phase 1 占位，Step 6 完整实现"""
from flask import redirect, url_for, session, current_app, request

from app.blueprints.main import main_bp


@main_bp.route('/')
def dashboard():
    """仪表盘 — 占位"""
    return '<h1>WaferCut MES Dashboard — TODO</h1>'


@main_bp.route('/set-language/<lang>')
def set_language(lang):
    """切换界���语言，存入 session，返回用户来源页"""
    supported = current_app.config.get('BABEL_SUPPORTED_LOCALES', ['zh'])
    if lang in supported:
        session['language'] = lang
    # 返回用户之前浏览的页面，而非始终跳转到仪表盘
    return redirect(request.referrer or url_for('main.dashboard'))
