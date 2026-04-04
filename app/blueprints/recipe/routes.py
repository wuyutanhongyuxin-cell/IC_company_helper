"""
参数库路由 — Recipe CRUD + 版本历史
Admin 可创建/编辑，所有已登录用户可查看
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from flask_babel import gettext as _
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.blueprints.recipe import recipe_bp
from app.extensions import db
from app.models.recipe import Recipe
from app.models.audit_log import log_action
from app.forms.recipe import RecipeForm
from app.utils.decorators import role_required

# Recipe 模型中所有参数字段名（用于表单填充和版本变更对比）
# !! 新增 Recipe 模型字段时，必须同步更新此列表 !!
_RECIPE_FIELDS = [
    'wafer_material', 'wafer_size', 'thickness', 'blade_model',
    'spindle_speed', 'feed_rate', 'cut_depth', 'coolant_flow',
    'max_chipping', 'cut_direction', 'z1_height', 'z2_height',
    'kerf_width', 'notes',
]


@recipe_bp.route('/')
@login_required
def list_recipes():
    """配方列表 — 只显示每组最新版本 (is_active=True)，支持材料/尺寸筛选"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)

    query = db.select(Recipe).filter_by(is_active=True).options(
        joinedload(Recipe.creator)
    )
    material = request.args.get('material', '').strip()
    if material:
        query = query.filter(Recipe.wafer_material == material)

    size = request.args.get('size', '').strip()
    if size:
        query = query.filter(Recipe.wafer_size == size)

    query = query.order_by(Recipe.created_at.desc())
    pagination = db.paginate(query, page=page, per_page=per_page)

    materials = db.session.execute(
        db.select(Recipe.wafer_material).filter_by(is_active=True).distinct()
    ).scalars().all()
    sizes = db.session.execute(
        db.select(Recipe.wafer_size).filter_by(is_active=True).distinct()
    ).scalars().all()

    return render_template(
        'recipe/list.html',
        pagination=pagination,
        materials=sorted(materials),
        sizes=sorted(sizes),
        current_material=material,
        current_size=size,
    )


@recipe_bp.route('/create', methods=['GET', 'POST'])
@role_required('admin')
def create_recipe():
    """创建新配方 — Admin 专用"""
    form = RecipeForm()
    if form.validate_on_submit():
        max_gid = db.session.execute(
            db.select(func.max(Recipe.recipe_group_id))
        ).scalar() or 0

        recipe = Recipe(
            recipe_group_id=max_gid + 1,
            version=1,
            created_by=current_user.id,
        )
        _populate_recipe(recipe, form)

        db.session.add(recipe)
        db.session.flush()  # 获取 recipe.id 用于审计日志
        log_action(
            current_user.id, 'create', 'recipe', recipe.id,
            details={'material': recipe.wafer_material, 'size': recipe.wafer_size},
        )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Recipe 创建提交失败')
            flash(_('保存失败，请重试'), 'danger')
            return render_template('recipe/form.html', form=form, is_edit=False)
        flash(_('配方创建成功'), 'success')
        return redirect(url_for('recipe.detail_recipe', id=recipe.id))

    return render_template('recipe/form.html', form=form, is_edit=False)


@recipe_bp.route('/<int:id>')
@login_required
def detail_recipe(id):
    """查看配方详情 — 显示具体版本信息"""
    recipe = db.get_or_404(Recipe, id)
    return render_template('recipe/detail.html', recipe=recipe)


@recipe_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_recipe(id):
    """编辑配方 — 创建新版本 (version+1)，旧行 is_active=False"""
    old_recipe = db.get_or_404(Recipe, id)

    # 只能编辑最新版本
    if not old_recipe.is_active:
        flash(_('只能编辑最新版本的配方'), 'warning')
        return redirect(url_for('recipe.detail_recipe', id=id))

    form = RecipeForm(obj=old_recipe)

    if form.validate_on_submit():
        changes = _collect_changes(old_recipe, form)
        new_recipe = Recipe(
            recipe_group_id=old_recipe.recipe_group_id,
            version=old_recipe.version + 1,
            created_by=current_user.id,
        )
        _populate_recipe(new_recipe, form)

        old_recipe.is_active = False

        db.session.add(new_recipe)
        db.session.flush()
        log_action(
            current_user.id, 'update', 'recipe', new_recipe.id,
            details={'from_version': old_recipe.version, 'changes': changes},
        )
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Recipe 版本更新提交失败')
            # 并发编辑时 UniqueConstraint 会触发此分支
            flash(_('保存失败，配方可能已被他人修改，请刷新后重试'), 'danger')
            return redirect(url_for('recipe.detail_recipe', id=id))

        flash(_('配方已更新为 v%(ver)s', ver=new_recipe.version), 'success')
        return redirect(url_for('recipe.detail_recipe', id=new_recipe.id))

    return render_template(
        'recipe/form.html', form=form, recipe=old_recipe, is_edit=True,
    )


@recipe_bp.route('/group/<int:gid>/history')
@login_required
def recipe_history(gid):
    """版本历史 — 显示同 recipe_group_id 下所有版本"""
    recipes = db.session.execute(
        db.select(Recipe)
        .filter_by(recipe_group_id=gid)
        .options(joinedload(Recipe.creator))
        .order_by(Recipe.version.desc())
    ).scalars().all()

    if not recipes:
        flash(_('未找到该配方组'), 'warning')
        return redirect(url_for('recipe.list_recipes'))

    return render_template('recipe/history.html', recipes=recipes, group_id=gid)


# ---- 私有辅助函数 ----

def _populate_recipe(recipe, form):
    """将表单数据填充到 Recipe 对象"""
    for field_name in _RECIPE_FIELDS:
        value = getattr(form, field_name).data
        # SelectField 空字符串 -> None（数据库中 NULL 表示非 DISCO 设备）
        if field_name == 'cut_direction' and value == '':
            value = None
        setattr(recipe, field_name, value)


def _collect_changes(old_recipe, form):
    """对比旧版本与表单提交值，返回变更字典（用于审计日志）"""
    changes = {}
    for field_name in _RECIPE_FIELDS:
        old_val = getattr(old_recipe, field_name)
        new_val = getattr(form, field_name).data
        if field_name == 'cut_direction' and new_val == '':
            new_val = None
        if old_val != new_val:
            changes[field_name] = [old_val, new_val]
    return changes
