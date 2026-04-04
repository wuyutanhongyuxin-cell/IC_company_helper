"""参数库路由 — Phase 1 占位，Step 4 完整实现"""
from app.blueprints.recipe import recipe_bp


@recipe_bp.route('/')
def list_recipes():
    """配方列表 — 占位"""
    return '<h1>Recipes — TODO</h1>'
