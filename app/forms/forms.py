from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, URL, Optional

class DynamicFieldForm(FlaskForm):
    """نموذج للحقول الديناميكية"""
    field_name = StringField('اسم الحقل', validators=[DataRequired()])
    field_type = SelectField('نوع الحقل', choices=[
        ('text', 'نص'),
        ('textarea', 'نص طويل'),
        ('number', 'رقم'),
        ('date', 'تاريخ'),
        ('select', 'قائمة منسدلة')
    ], validators=[DataRequired()])
    field_options = TextAreaField('خيارات (للقائمة المنسدلة، افصل بين الخيارات بفاصلة)', validators=[Optional()])
    
    class Meta:
        # تعطيل حماية CSRF لهذا النموذج الفرعي
        csrf = False

class CategoryForm(FlaskForm):
    """نموذج إضافة/تعديل التصنيف"""
    name = StringField('اسم التصنيف', validators=[DataRequired()])
    dynamic_fields = FieldList(FormField(DynamicFieldForm), min_entries=0)
    submit = SubmitField('حفظ')

class NewsForm(FlaskForm):
    """نموذج إضافة/تعديل الخبر"""
    title = StringField('عنوان الخبر', validators=[DataRequired()])
    content = TextAreaField('تفاصيل الخبر', validators=[DataRequired()])
    date = DateField('التاريخ', validators=[DataRequired()])
    source = StringField('المصدر', validators=[DataRequired()])
    source_url = StringField('رابط المصدر', validators=[URL(), Optional()])
    governorate_id = SelectField('المحافظة', coerce=int, validators=[DataRequired()])
    category_id = SelectField('التصنيف', coerce=int, validators=[DataRequired()])
    # الحقول الديناميكية ستضاف بشكل برمجي بناءً على التصنيف المختار
    submit = SubmitField('حفظ')
