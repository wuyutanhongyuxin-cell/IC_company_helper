"""
认证相关表单 — 登录 / 用户创建 / 用户编辑 / 修改密码
所有标签使用 lazy_gettext 支持多语言
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField,
    BooleanField, SubmitField,
)
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_babel import lazy_gettext as _l

from app.extensions import db
from app.models.user import User

# 角色选项常量 — 避免多处硬编码
ROLE_CHOICES = [('operator', _l('操作员')), ('admin', _l('管理员'))]


class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField(
        _l('用户名'), validators=[DataRequired(), Length(1, 64)]
    )
    password = PasswordField(
        _l('密码'), validators=[DataRequired()]
    )
    submit = SubmitField(_l('登录'))


class UserCreateForm(FlaskForm):
    """创建用户表单（Admin 专用）"""
    username = StringField(
        _l('用户名'), validators=[DataRequired(), Length(1, 64)]
    )
    display_name = StringField(
        _l('显示名'), validators=[DataRequired(), Length(1, 64)]
    )
    password = PasswordField(
        _l('密码'), validators=[DataRequired(), Length(6, 128)]
    )
    password2 = PasswordField(
        _l('确认密码'),
        validators=[
            DataRequired(),
            EqualTo('password', message=_l('两次密码不一致')),
        ],
    )
    role = SelectField(_l('角色'), choices=ROLE_CHOICES)
    submit = SubmitField(_l('创建'))

    def validate_username(self, field):
        """校验用户名唯一性"""
        existing = db.session.execute(
            db.select(User).filter_by(username=field.data)
        ).scalar_one_or_none()
        if existing:
            raise ValidationError(_l('用户名已存在'))


class UserEditForm(FlaskForm):
    """编辑用户表单（Admin 专用）"""
    display_name = StringField(
        _l('显示名'), validators=[DataRequired(), Length(1, 64)]
    )
    role = SelectField(_l('角色'), choices=ROLE_CHOICES)
    is_active = BooleanField(_l('启用'))
    # 留空不改密码
    new_password = PasswordField(
        _l('新密码（留空不改）'), validators=[Length(0, 128)]
    )
    new_password2 = PasswordField(
        _l('确认新密码'),
        validators=[EqualTo('new_password', message=_l('两次密码不一致'))],
    )
    submit = SubmitField(_l('保存'))


class ChangePasswordForm(FlaskForm):
    """修改密码表单（本人使用）"""
    old_password = PasswordField(
        _l('当前密码'), validators=[DataRequired()]
    )
    new_password = PasswordField(
        _l('新密码'), validators=[DataRequired(), Length(6, 128)]
    )
    new_password2 = PasswordField(
        _l('确认新密码'),
        validators=[
            DataRequired(),
            EqualTo('new_password', message=_l('两次密码不一致')),
        ],
    )
    submit = SubmitField(_l('修改密码'))
