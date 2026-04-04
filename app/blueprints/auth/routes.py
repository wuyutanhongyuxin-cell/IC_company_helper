"""
认证路由 — 登录/登出/用户管理/修改密码
Admin 可管理用户，所有用户可改自己密码
"""
from urllib.parse import urlparse

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import gettext as _

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.models.user import User
from app.models.audit_log import log_action
from app.forms.auth import (
    LoginForm, UserCreateForm, UserEditForm, ChangePasswordForm,
)
from app.utils.decorators import role_required


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页 — 已登录用户自动跳转仪表盘"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data)
        ).scalar_one_or_none()

        if user is None or not user.check_password(form.password.data):
            flash(_('用户名或密码错误'), 'danger')
            return render_template('auth/login.html', form=form)

        if not user.is_active:
            flash(_('账号已被禁用，请联系管理员'), 'danger')
            return render_template('auth/login.html', form=form)

        login_user(user)
        # 审计日志: commit 失败不应阻止登录
        try:
            log_action(user.id, 'login', 'user', user.id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception('登录审计日志写入失败')

        # 安全校验: 拒绝协议相对 URL (//evil.com) 和绝对 URL
        next_page = request.args.get('next', '')
        if not next_page or urlparse(next_page).netloc:
            next_page = url_for('main.dashboard')

        flash(_('登录成功'), 'success')
        return redirect(next_page)

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """登出 — POST 防止 CSRF 强制登出，记录审计日志后清除会话"""
    try:
        log_action(current_user.id, 'logout', 'user', current_user.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('登出审计日志写入失败')
    logout_user()
    flash(_('已登出'), 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
@role_required('admin')
def users():
    """用户列表 — 仅 Admin 可访问"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    pagination = db.paginate(
        db.select(User).order_by(User.created_at.desc()),
        page=page, per_page=per_page,
    )
    return render_template('auth/users.html', pagination=pagination)


@auth_bp.route('/users/create', methods=['GET', 'POST'])
@role_required('admin')
def user_create():
    """创建用户 — 仅 Admin"""
    form = UserCreateForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            display_name=form.display_name.data,
            role=form.role.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # 刷入数据库获取 user.id，但不提交事务
        log_action(
            current_user.id, 'create', 'user', user.id,
            details={'username': user.username, 'role': user.role},
        )
        db.session.commit()
        flash(_('用户 %(name)s 创建成功', name=user.display_name), 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/user_form.html', form=form, is_edit=False)


@auth_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def user_edit(id):
    """编辑用户 — 仅 Admin，可修改角色/状态/重置密码"""
    user = db.get_or_404(User, id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        # 防止 admin 禁用/降级自己 — 避免系统无管理员
        if user.id == current_user.id:
            if not form.is_active.data:
                flash(_('不能禁用自己的账号'), 'danger')
                return render_template(
                    'auth/user_form.html', form=form, user=user, is_edit=True)
            if form.role.data != 'admin':
                flash(_('不能降低自己的权限'), 'danger')
                return render_template(
                    'auth/user_form.html', form=form, user=user, is_edit=True)

        # 记录变更详情
        changes = _collect_user_changes(user, form)
        # 应用变更
        user.display_name = form.display_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        if form.new_password.data:
            user.set_password(form.new_password.data)
            changes['password'] = _('已重置')

        log_action(current_user.id, 'update', 'user', user.id, details=changes)
        db.session.commit()
        flash(_('用户 %(name)s 已更新', name=user.display_name), 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/user_form.html', form=form, user=user, is_edit=True)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码 — 任何已登录用户"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash(_('当前密码错误'), 'danger')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        log_action(
            current_user.id, 'update', 'user', current_user.id,
            details={'password': _('已修改')},
        )
        db.session.commit()
        flash(_('密码修改成功'), 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/change_password.html', form=form)


def _collect_user_changes(user, form):
    """对比用户当前值与表单提交值，返回变更字典（用于审计日志）"""
    changes = {}
    if user.display_name != form.display_name.data:
        changes['display_name'] = [user.display_name, form.display_name.data]
    if user.role != form.role.data:
        changes['role'] = [user.role, form.role.data]
    if user.is_active != form.is_active.data:
        changes['is_active'] = [user.is_active, form.is_active.data]
    return changes
