"""
Recipe 表单 — 切割参数创建/编辑
所有标签使用 lazy_gettext 支持多语言
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, FloatField, IntegerField, SelectField,
    TextAreaField, SubmitField,
)
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from flask_babel import lazy_gettext as _l


def _str_or_empty(val):
    """None -> '' 用于可选 SelectField (避免 obj=recipe 时 None 不匹配空字符串选项)"""
    return '' if val is None else str(val)


# 切割方向选项 — 空值表示非 DISCO 设备
CUT_DIRECTION_CHOICES = [
    ('', _l('不适用')),
    ('X', 'X'),
    ('Y', 'Y'),
]


class RecipeForm(FlaskForm):
    """切割参数配方表单（创建/编辑共用）"""

    # ---- 基础切割参数 ----
    wafer_material = StringField(
        _l('材料类型'), validators=[DataRequired(), Length(1, 64)]
    )
    wafer_size = StringField(
        _l('晶圆尺寸'), validators=[DataRequired(), Length(1, 32)]
    )
    thickness = FloatField(
        _l('厚度(um)'), validators=[DataRequired(), NumberRange(min=0)]
    )
    blade_model = StringField(
        _l('刀片型号'), validators=[DataRequired(), Length(1, 64)]
    )
    spindle_speed = IntegerField(
        _l('主轴转速(RPM)'), validators=[DataRequired(), NumberRange(min=0)]
    )
    feed_rate = FloatField(
        _l('进给速度(mm/s)'), validators=[DataRequired(), NumberRange(min=0)]
    )
    cut_depth = FloatField(
        _l('切割深度(um)'), validators=[DataRequired(), NumberRange(min=0)]
    )
    coolant_flow = FloatField(
        _l('冷却水流量(L/min)'), validators=[DataRequired(), NumberRange(min=0)]
    )
    max_chipping = FloatField(
        _l('最大允许崩边(um)'), validators=[DataRequired(), NumberRange(min=0)]
    )

    # ---- DISCO 切割机参数（可选）----
    cut_direction = SelectField(
        _l('切割方向'),
        choices=CUT_DIRECTION_CHOICES,
        coerce=_str_or_empty,
    )
    z1_height = FloatField(
        _l('Z1 高度(um)'), validators=[Optional(), NumberRange(min=0)]
    )
    z2_height = FloatField(
        _l('Z2 高度(um)'), validators=[Optional(), NumberRange(min=0)]
    )
    kerf_width = FloatField(
        _l('切口宽度(um)'), validators=[Optional(), NumberRange(min=0)]
    )

    # ---- 备注 ----
    notes = TextAreaField(
        _l('备注'), validators=[Optional(), Length(0, 2000)]
    )

    submit = SubmitField(_l('保存'))
