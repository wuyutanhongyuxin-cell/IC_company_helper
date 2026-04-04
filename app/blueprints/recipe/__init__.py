"""参数库蓝图 — Recipe CRUD + 版本历史"""
from flask import Blueprint

recipe_bp = Blueprint('recipe', __name__, url_prefix='/recipes')

from app.blueprints.recipe import routes  # noqa: E402, F401
