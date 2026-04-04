"""
工单/检验表单 — 创建、编辑、检验数据填写
所有标签使用 lazy_gettext 支持多语言
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, FloatField, SelectField,
    TextAreaField, SubmitField,
)
from wtforms.validators import DataRequired, InputRequired, NumberRange, Optional, Length
from flask_babel import lazy_gettext as _l


class WorkOrderForm(FlaskForm):
    """创建/编辑工单表单"""
    customer = StringField(
        _l('客户名称'), validators=[DataRequired(), Length(1, 128)]
    )
    wafer_spec = StringField(
        _l('晶圆规格'), validators=[DataRequired(), Length(1, 256)]
    )
    quantity = IntegerField(
        _l('数量(片)'), validators=[DataRequired(), NumberRange(min=1)]
    )
    # recipe_id 用 SelectField，choices 在路由中动态填充
    recipe_id = SelectField(
        _l('切割配方'), coerce=int, validators=[DataRequired()]
    )
    submit = SubmitField(_l('保存'))


class InspectionForm(FlaskForm):
    """检验数据填写表单"""
    # InputRequired 替代 DataRequired: 允许 0 值 (良率 0% / 崩边 0um 是合法的)
    yield_rate = FloatField(
        _l('良率(%)'), validators=[InputRequired(), NumberRange(min=0, max=100)]
    )
    max_chipping_actual = FloatField(
        _l('崩边实测(um)'), validators=[InputRequired(), NumberRange(min=0)]
    )
    inspection_result = SelectField(
        _l('检验结果'),
        choices=[('pass', _l('通过')), ('fail', _l('不通过'))],
        validators=[DataRequired()],
    )
    inspection_notes = TextAreaField(
        _l('检验备注'), validators=[Optional(), Length(0, 2000)]
    )
    submit = SubmitField(_l('提交检验'))


class StatusForm(FlaskForm):
    """状态推进表单（含可选备注）"""
    notes = TextAreaField(
        _l('操作备注'), validators=[Optional(), Length(0, 500)]
    )
    submit = SubmitField(_l('确认'))
