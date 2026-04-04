"""参数库路由 — Phase 1 占位，Step 4 完整实现"""
from flask_login import login_required

from app.blueprints.recipe import recipe_bp


@recipe_bp.route('/')
@login_required
def list_recipes():
    """配方列表 — 占位，Step 4 完整实现"""
    return '<h1>Recipes — TODO Step 4</h1>'
