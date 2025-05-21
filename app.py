from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, make_response, send_file, session, abort
from flask_migrate import Migrate
from datetime import datetime, date, timedelta
import json
import os
import sys
import pdfkit
import locale
import shutil
import sqlite3
from sqlalchemy import and_, or_
from datetime import datetime, date
from werkzeug.utils import secure_filename

# تعطيل استخدام pdfkit
pdf_enabled = False

# دالة لتحويل التاريخ إلى اللغة العربية
def format_date_arabic(date_obj, format_type='full'):
    """
    تحويل التاريخ إلى اللغة العربية بعدة صيغ

    :param date_obj: كائن التاريخ
    :param format_type: نوع الصيغة ('full', 'medium', 'short', 'day_month', 'month_year', 'numeric')
    :return: التاريخ بالصيغة العربية
    """
    if not date_obj:
        return ""

    # قائمة بأسماء الأيام باللغة العربية
    arabic_days = [
        "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"
    ]

    # قائمة بأسماء الأيام المختصرة باللغة العربية
    arabic_days_short = [
        "اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"
    ]

    # قائمة بأسماء الأشهر باللغة العربية (مصر والخليج)
    arabic_months_egypt = [
        "يناير", "فبراير", "مارس", "إبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]

    # قائمة بأسماء الأشهر باللغة العربية (العراق وسوريا ولبنان وفلسطين والأردن)
    arabic_months_levant = [
        "كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران",
        "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"
    ]

    # الحصول على اليوم والشهر والسنة
    day_name = arabic_days[date_obj.weekday()]
    day_name_short = arabic_days_short[date_obj.weekday()]
    day = date_obj.day
    month_egypt = arabic_months_egypt[date_obj.month - 1]
    month_levant = arabic_months_levant[date_obj.month - 1]
    year = date_obj.year

    # تنسيق التاريخ بالعربية حسب النوع المطلوب
    if format_type == 'full':
        # مثال: الخميس 17 مايو 2024
        formatted_date = f"{day_name} {day} {month_egypt} {year}"
    elif format_type == 'full_levant':
        # مثال: الخميس 17 أيار 2024
        formatted_date = f"{day_name} {day} {month_levant} {year}"
    elif format_type == 'medium':
        # مثال: 17 مايو 2024
        formatted_date = f"{day} {month_egypt} {year}"
    elif format_type == 'medium_levant':
        # مثال: 17 أيار 2024
        formatted_date = f"{day} {month_levant} {year}"
    elif format_type == 'short':
        # مثال: 17 مايو
        formatted_date = f"{day} {month_egypt}"
    elif format_type == 'short_levant':
        # مثال: 17 أيار
        formatted_date = f"{day} {month_levant}"
    elif format_type == 'day_month':
        # مثال: الخميس 17 مايو
        formatted_date = f"{day_name} {day} {month_egypt}"
    elif format_type == 'day_month_levant':
        # مثال: الخميس 17 أيار
        formatted_date = f"{day_name} {day} {month_levant}"
    elif format_type == 'month_year':
        # مثال: مايو 2024
        formatted_date = f"{month_egypt} {year}"
    elif format_type == 'month_year_levant':
        # مثال: أيار 2024
        formatted_date = f"{month_levant} {year}"
    elif format_type == 'numeric':
        # مثال: 17/05/2024
        formatted_date = f"{day:02d}/{date_obj.month:02d}/{year}"
    elif format_type == 'numeric_dash':
        # مثال: 17-05-2024
        formatted_date = f"{day:02d}-{date_obj.month:02d}-{year}"
    else:
        # الصيغة الافتراضية
        formatted_date = f"{day_name} {day} {month_egypt} {year}"

    return formatted_date

# إضافة المجلد الحالي إلى مسار البحث
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from config import Config

# إنشاء تطبيق Flask
app = Flask(__name__,
            template_folder='app/templates',
            static_folder='app/static')
app.config.from_object(Config)

# إضافة دالة مساعدة لتنسيق التاريخ في قوالب Jinja2
@app.template_filter('format_date_arabic')
def format_date_arabic_filter(date_obj, format_type='full'):
    """
    فلتر Jinja2 لتنسيق التاريخ بالعربية

    :param date_obj: كائن التاريخ
    :param format_type: نوع الصيغة ('full', 'medium', 'short', 'day_month', 'month_year', 'numeric')
    :return: التاريخ بالصيغة العربية
    """
    return format_date_arabic(date_obj, format_type)

# تغيير اسم قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('app.db', 'relational_app.db')

# استخدام النماذج العلائقية الجديدة
from app.models.relational_models import db, News, Category, Governorate, Field, FieldValue, NewsSource, SourceType, init_governorates
import logging

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

# تهيئة قاعدة البيانات
db.init_app(app)
migrate = Migrate(app, db)

# تم إزالة تهيئة المجدول

# إضافة فلتر nl2br لتحويل السطور الجديدة إلى وسوم <br>
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        # تحويل السطور الجديدة إلى وسوم <br>
        value = value.replace('\n', '<br>\n')
        # معالجة وسوم <br> المكتوبة كنص
        value = value.replace('&lt;br&gt;', '<br>')
        value = value.replace('<br>', '<br>')
    return value

# دالة لتنسيق التاريخ باللغة العربية
def format_date_arabic(date_obj, format_type='default'):
    if not date_obj:
        return ""

    arabic_months = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
        7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }

    arabic_months_levant = {
        1: "كانون الثاني", 2: "شباط", 3: "آذار", 4: "نيسان", 5: "أيار", 6: "حزيران",
        7: "تموز", 8: "آب", 9: "أيلول", 10: "تشرين الأول", 11: "تشرين الثاني", 12: "كانون الأول"
    }

    # قائمة بأسماء الأيام باللغة العربية
    arabic_days = {
        0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"
    }

    if format_type == 'full_with_day':
        # مثال: يوم الخميس 17 مايو 2024
        day_name = arabic_days[date_obj.weekday()]
        return f"يوم {day_name} {date_obj.day} {arabic_months[date_obj.month]} {date_obj.year}"
    elif format_type == 'full_with_day_levant':
        # مثال: يوم الخميس 17 أيار 2024
        day_name = arabic_days[date_obj.weekday()]
        return f"يوم {day_name} {date_obj.day} {arabic_months_levant[date_obj.month]} {date_obj.year}"
    elif format_type == 'full_levant':
        return f"{date_obj.day} {arabic_months_levant[date_obj.month]} {date_obj.year}"
    elif format_type == 'full':
        return f"{date_obj.day} {arabic_months[date_obj.month]} {date_obj.year}"
    else:
        return f"{date_obj.day}/{date_obj.month}/{date_obj.year}"

# تمكين استخدام وسوم HTML آمنة في القوالب
app.jinja_env.filters['nl2br'] = nl2br
app.jinja_env.filters['format_date_arabic'] = format_date_arabic
app.jinja_env.autoescape = False

# دالة تنفذ قبل كل طلب لتمرير أحدث الأخبار إلى جميع القوالب
@app.context_processor
def inject_latest_news():
    latest_news = News.query.order_by(News.date.desc()).limit(5).all()
    return dict(latest_news=latest_news)

with app.app_context():
    db.create_all()
    init_governorates(db.session)

# الصفحة الرئيسية
@app.route('/')
def index():
    # جلب آخر 10 أخبار
    latest_news = News.query.order_by(News.date.desc()).limit(10).all()

    # جلب أخبار مميزة (أحدث 6 أخبار من تصنيفات مختلفة)
    featured_news = News.query.order_by(News.date.desc()).limit(6).all()

    # جلب التصنيفات
    categories = Category.query.all()

    # جلب المحافظات
    governorates = Governorate.query.all()

    # الوقت الحالي لحساب الوقت المنقضي
    now = datetime.now()

    # إحصائيات النظام
    news_count = News.query.count()
    categories_count = Category.query.count()
    governorates_count = Governorate.query.count()
    today = format_date_arabic(date.today())

    return render_template('index.html',
                          latest_news=latest_news,
                          featured_news=featured_news,
                          categories=categories,
                          governorates=governorates,
                          news_count=news_count,
                          categories_count=categories_count,
                          governorates_count=governorates_count,
                          today=today,
                          now=now)

# صفحة إضافة خبر جديد
@app.route('/news/add', methods=['GET', 'POST'])
def add_news():
    if request.method == 'POST':
        # استلام بيانات النموذج
        title = request.form.get('title')
        content = request.form.get('content')
        # معالجة وسوم <br> في المحتوى
        content = content.replace('<br>', '\n')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        source = request.form.get('source')
        source_url = request.form.get('source_url')
        governorate_id = request.form.get('governorate_id', type=int)
        category_id = request.form.get('category_id', type=int)

        # إنشاء خبر جديد
        news = News(
            title=title,
            content=content,
            date=date,
            source=source,
            source_url=source_url,
            governorate_id=governorate_id,
            category_id=category_id
        )
        db.session.add(news)
        db.session.flush()  # للحصول على معرف الخبر الجديد

        # معالجة الحقول الديناميكية
        category = Category.query.get(category_id)
        fields = Field.query.filter_by(category_id=category_id).all()

        for field in fields:
            field_value = request.form.get(f'field_{field.id}')
            if field_value:
                field_value_obj = FieldValue(
                    news_id=news.id,
                    field_id=field.id,
                    value=field_value
                )
                db.session.add(field_value_obj)

        db.session.commit()
        flash('تمت إضافة الخبر بنجاح', 'success')
        return redirect(url_for('view_news'))

    # عرض نموذج إضافة خبر
    governorates = Governorate.query.all()
    categories = Category.query.all()

    return render_template('add_news.html',
                           governorates=governorates,
                           categories=categories)

# الحصول على الحقول الديناميكية للتصنيف المحدد
@app.route('/api/category/<int:category_id>/fields')
def get_category_fields(category_id):
    fields = Field.query.filter_by(category_id=category_id).order_by(Field.order).all()
    fields_data = []

    for field in fields:
        field_data = {
            'id': field.id,
            'name': field.name,
            'type': field.field_type,
            'required': field.required,
            'options': field.get_options() if field.field_type == 'select' else []
        }
        fields_data.append(field_data)

    return jsonify(fields_data)

# صفحة عرض الأخبار
@app.route('/news')
def view_news():
    # تحديد رقم الصفحة وعدد العناصر في الصفحة
    page = request.args.get('page', 1, type=int)
    per_page = 20  # عدد الأخبار في الصفحة الواحدة

    # استلام معايير الفلترة
    category_id = request.args.get('category_id', '')
    governorate_id = request.args.get('governorate_id', '')
    date_filter = request.args.get('date', '')
    search_query = request.args.get('search', '')

    # إنشاء استعلام الأخبار
    query = News.query

    # تطبيق معايير الفلترة
    if category_id and category_id.isdigit():
        query = query.filter(News.category_id == int(category_id))

    if governorate_id and governorate_id.isdigit():
        query = query.filter(News.governorate_id == int(governorate_id))

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(News.date == filter_date)
        except ValueError:
            # في حالة وجود خطأ في تنسيق التاريخ، تجاهل هذا الفلتر
            pass

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                News.title.like(search_term),
                News.content.like(search_term),
                News.source.like(search_term)
            )
        )

    # ترتيب الأخبار حسب التاريخ تنازلياً
    query = query.order_by(News.date.desc())

    # تطبيق تقسيم الصفحات
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    news_list = pagination.items
    categories = Category.query.all()
    governorates = Governorate.query.all()

    return render_template('view_news.html',
                          news_list=news_list,
                          categories=categories,
                          governorates=governorates,
                          pagination=pagination,
                          category_id=category_id,
                          governorate_id=governorate_id,
                          date_filter=date_filter,
                          search_query=search_query)

# صفحة عرض الأخبار حسب التصنيف
@app.route('/news/category/<int:category_id>')
def view_news_by_category(category_id):
    category = Category.query.get_or_404(category_id)
    news_list = News.query.filter_by(category_id=category_id).order_by(News.date.desc()).all()
    categories = Category.query.all()
    governorates = Governorate.query.all()

    # الوقت الحالي لحساب الوقت المنقضي
    now = datetime.now()

    return render_template('news_by_category.html',
                          news_list=news_list,
                          category=category,
                          categories=categories,
                          governorates=governorates,
                          now=now)

# صفحة عرض الأخبار حسب المحافظة
@app.route('/news/governorate/<int:governorate_id>')
def view_news_by_governorate(governorate_id):
    governorate = Governorate.query.get_or_404(governorate_id)
    news_list = News.query.filter_by(governorate_id=governorate_id).order_by(News.date.desc()).all()
    categories = Category.query.all()
    governorates = Governorate.query.all()

    # الوقت الحالي لحساب الوقت المنقضي
    now = datetime.now()

    return render_template('news_by_governorate.html',
                          news_list=news_list,
                          governorate=governorate,
                          categories=categories,
                          governorates=governorates,
                          now=now)

# صفحة عرض تفاصيل الخبر
@app.route('/news/<int:news_id>')
def view_news_details(news_id):
    news = News.query.get_or_404(news_id)
    field_values = FieldValue.query.filter_by(news_id=news_id).all()

    # تنظيم قيم الحقول
    field_data = []
    for fv in field_values:
        field = Field.query.get(fv.field_id)
        field_data.append({
            'name': field.name,
            'value': fv.value,
            'type': field.field_type
        })

    return render_template('news_details.html', news=news, field_data=field_data)

# صفحة تعديل الخبر
@app.route('/news/edit/<int:news_id>', methods=['GET', 'POST'])
def edit_news(news_id):
    news = News.query.get_or_404(news_id)

    if request.method == 'POST':
        # استلام بيانات النموذج
        news.title = request.form.get('title')
        content = request.form.get('content')
        # معالجة وسوم <br> في المحتوى
        content = content.replace('<br>', '\n')
        news.content = content
        news.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        news.source = request.form.get('source')
        news.source_url = request.form.get('source_url')
        news.governorate_id = request.form.get('governorate_id', type=int)
        news.category_id = request.form.get('category_id', type=int)

        # حذف قيم الحقول الديناميكية القديمة
        FieldValue.query.filter_by(news_id=news_id).delete()

        # معالجة الحقول الديناميكية الجديدة
        fields = Field.query.filter_by(category_id=news.category_id).all()

        for field in fields:
            field_value = request.form.get(f'field_{field.id}')
            if field_value:
                field_value_obj = FieldValue(
                    news_id=news.id,
                    field_id=field.id,
                    value=field_value
                )
                db.session.add(field_value_obj)

        db.session.commit()
        flash('تم تعديل الخبر بنجاح', 'success')
        return redirect(url_for('view_news_details', news_id=news.id))

    # عرض نموذج تعديل الخبر
    governorates = Governorate.query.all()
    categories = Category.query.all()
    field_values = FieldValue.query.filter_by(news_id=news_id).all()

    return render_template('edit_news.html',
                           news=news,
                           governorates=governorates,
                           categories=categories,
                           field_values=field_values)

# حذف الخبر
@app.route('/news/delete/<int:news_id>', methods=['POST'])
def delete_news(news_id):
    news = News.query.get_or_404(news_id)

    # حذف قيم الحقول الديناميكية المرتبطة بالخبر
    FieldValue.query.filter_by(news_id=news_id).delete()

    # حذف الخبر
    db.session.delete(news)
    db.session.commit()

    flash('تم حذف الخبر بنجاح', 'success')
    return redirect(url_for('view_news'))

# صفحة طباعة الأخبار
@app.route('/news/print')
def print_news():
    # استلام معايير البحث
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    category_id = request.args.get('category_id', '')

    # إنشاء استعلام الأخبار
    query = News.query

    # تطبيق معايير البحث
    if start_date:
        query = query.filter(News.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(News.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if category_id and category_id.isdigit():
        query = query.filter(News.category_id == int(category_id))

    # ترتيب الأخبار حسب التاريخ تنازلياً
    news_list = query.order_by(News.date.desc()).all()

    # جلب التصنيفات للفلتر
    categories = Category.query.all()

    # تحضير بيانات القالب
    today_date = format_date_arabic(date.today())
    current_year = date.today().year

    return render_template('print_news.html',
                          news_list=news_list,
                          categories=categories,
                          today_date=today_date,
                          current_year=current_year)

# تصدير الأخبار إلى PDF
@app.route('/news/export/pdf')
def export_news_pdf():
    # استلام معايير البحث
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    category_id = request.args.get('category_id', '')

    # إنشاء استعلام الأخبار
    query = News.query

    # تطبيق معايير البحث
    if start_date:
        query = query.filter(News.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(News.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if category_id and category_id.isdigit():
        query = query.filter(News.category_id == int(category_id))

    # ترتيب الأخبار حسب التاريخ تنازلياً
    news_list = query.order_by(News.date.desc()).all()

    # تحضير بيانات القالب
    today = date.today()
    today_date = format_date_arabic(today, 'full_with_day')  # استخدام تنسيق يشمل اسم اليوم
    current_year = today.year

    # عرض قالب PDF مباشرة
    return render_template('pdf_template.html',
                          news_list=news_list,
                          today_date=today_date,
                          current_year=current_year)

# صفحة إدارة التصنيفات
@app.route('/categories', methods=['GET'])
def manage_categories():
    categories = Category.query.all()

    # إضافة عدد الحقول لكل تصنيف
    categories_data = []
    for category in categories:
        fields_count = Field.query.filter_by(category_id=category.id).count()
        categories_data.append({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'fields_count': fields_count
        })

    return render_template('manage_categories.html', categories=categories_data)

# صفحة إضافة تصنيف جديد
@app.route('/categories/add', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # إنشاء تصنيف جديد
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.flush()  # للحصول على معرف التصنيف الجديد

        # معالجة الحقول الديناميكية
        field_names = request.form.getlist('field_name')
        field_types = request.form.getlist('field_type')
        field_required = request.form.getlist('field_required')
        field_options = request.form.getlist('field_options')

        for i in range(len(field_names)):
            if field_names[i]:
                field = Field(
                    name=field_names[i],
                    field_type=field_types[i],
                    required=i < len(field_required) and field_required[i] == 'on',
                    category_id=category.id,
                    order=i
                )

                # إضافة الخيارات إذا كان نوع الحقل قائمة منسدلة
                if field.field_type == 'select' and i < len(field_options) and field_options[i]:
                    options = [opt.strip() for opt in field_options[i].split(',') if opt.strip()]
                    field.set_options(options)

                db.session.add(field)

        db.session.commit()
        flash('تمت إضافة التصنيف بنجاح', 'success')
        return redirect(url_for('manage_categories'))

    return render_template('add_category.html')

# صفحة تعديل تصنيف
@app.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    fields = Field.query.filter_by(category_id=category_id).order_by(Field.order).all()

    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')

        # حذف الحقول القديمة
        for field in fields:
            db.session.delete(field)

        # إضافة الحقول الجديدة
        field_names = request.form.getlist('field_name')
        field_types = request.form.getlist('field_type')
        field_required = request.form.getlist('field_required')
        field_options = request.form.getlist('field_options')

        for i in range(len(field_names)):
            if field_names[i]:
                field = Field(
                    name=field_names[i],
                    field_type=field_types[i],
                    required=i < len(field_required) and field_required[i] == 'on',
                    category_id=category.id,
                    order=i
                )

                # إضافة الخيارات إذا كان نوع الحقل قائمة منسدلة
                if field.field_type == 'select' and i < len(field_options) and field_options[i]:
                    options = [opt.strip() for opt in field_options[i].split(',') if opt.strip()]
                    field.set_options(options)

                db.session.add(field)

        db.session.commit()
        flash('تم تعديل التصنيف بنجاح', 'success')
        return redirect(url_for('manage_categories'))

    return render_template('edit_category.html', category=category, fields=fields)

# حذف تصنيف
@app.route('/categories/delete/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)

    # التحقق من عدم وجود أخبار مرتبطة بهذا التصنيف
    if News.query.filter_by(category_id=category_id).count() > 0:
        flash('لا يمكن حذف التصنيف لأنه يحتوي على أخبار', 'danger')
        return redirect(url_for('manage_categories'))

    # حذف الحقول المرتبطة بالتصنيف
    fields = Field.query.filter_by(category_id=category_id).all()
    for field in fields:
        db.session.delete(field)

    # حذف التصنيف
    db.session.delete(category)
    db.session.commit()
    flash('تم حذف التصنيف بنجاح', 'success')
    return redirect(url_for('manage_categories'))

# صفحة إدارة المحافظات
@app.route('/governorates')
def manage_governorates():
    governorates = Governorate.query.all()

    # إضافة عدد الأخبار لكل محافظة
    governorates_data = []
    for governorate in governorates:
        news_count = News.query.filter_by(governorate_id=governorate.id).count()
        governorates_data.append({
            'id': governorate.id,
            'name': governorate.name,
            'news_count': news_count
        })

    return render_template('manage_governorates.html', governorates=governorates_data)

# إضافة محافظة جديدة
@app.route('/governorates/add', methods=['POST'])
def add_governorate():
    name = request.form.get('name')

    # التحقق من عدم وجود محافظة بنفس الاسم
    if Governorate.query.filter_by(name=name).first():
        flash('المحافظة موجودة بالفعل', 'danger')
        return redirect(url_for('manage_governorates'))

    # إنشاء محافظة جديدة
    governorate = Governorate(name=name)
    db.session.add(governorate)
    db.session.commit()

    flash('تمت إضافة المحافظة بنجاح', 'success')
    return redirect(url_for('manage_governorates'))

# تعديل محافظة
@app.route('/governorates/edit/<int:governorate_id>', methods=['POST'])
def edit_governorate(governorate_id):
    governorate = Governorate.query.get_or_404(governorate_id)
    name = request.form.get('name')

    # التحقق من عدم وجود محافظة أخرى بنفس الاسم
    existing = Governorate.query.filter_by(name=name).first()
    if existing and existing.id != governorate_id:
        flash('يوجد محافظة أخرى بنفس الاسم', 'danger')
        return redirect(url_for('manage_governorates'))

    # تعديل المحافظة
    governorate.name = name
    db.session.commit()

    flash('تم تعديل المحافظة بنجاح', 'success')
    return redirect(url_for('manage_governorates'))

# حذف محافظة
@app.route('/governorates/delete/<int:governorate_id>', methods=['POST'])
def delete_governorate(governorate_id):
    governorate = Governorate.query.get_or_404(governorate_id)

    # التحقق من عدم وجود أخبار مرتبطة بهذه المحافظة
    if News.query.filter_by(governorate_id=governorate_id).count() > 0:
        flash('لا يمكن حذف المحافظة لأنها تحتوي على أخبار', 'danger')
        return redirect(url_for('manage_governorates'))

    # حذف المحافظة
    db.session.delete(governorate)
    db.session.commit()

    flash('تم حذف المحافظة بنجاح', 'success')
    return redirect(url_for('manage_governorates'))

# صفحة إدارة مصادر الأخبار (إعادة توجيه إلى صفحة الجلب التلقائي الموحدة)
@app.route('/sources')
def manage_sources():
    return redirect(url_for('auto_news', _anchor='sources'))

# إضافة مصدر جديد
@app.route('/sources/add', methods=['POST'])
def add_source():
    name = request.form.get('name')
    url = request.form.get('url')
    source_type = request.form.get('source_type', SourceType.WEBSITE.value)
    is_active = 'is_active' in request.form

    # إنشاء مصدر جديد
    source = NewsSource(
        name=name,
        url=url,
        source_type=source_type,
        is_active=is_active
    )

    # تحديد ما إذا كان المصدر عراقي
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    source.is_iraqi = '.iq' in domain or any(keyword in domain for keyword in ['iraq', 'عراق'])

    db.session.add(source)
    db.session.commit()

    flash('تمت إضافة المصدر بنجاح', 'success')
    return redirect(url_for('auto_news', _anchor='sources'))

# تعديل مصدر
@app.route('/sources/edit/<int:source_id>', methods=['POST'])
def edit_source(source_id):
    source = NewsSource.query.get_or_404(source_id)

    source.name = request.form.get('name')
    source.url = request.form.get('url')
    source.source_type = request.form.get('source_type', SourceType.WEBSITE.value)
    source.is_active = 'is_active' in request.form

    # تحديد ما إذا كان المصدر عراقي
    from urllib.parse import urlparse
    domain = urlparse(source.url).netloc
    source.is_iraqi = '.iq' in domain or any(keyword in domain for keyword in ['iraq', 'عراق'])

    db.session.commit()

    flash('تم تعديل المصدر بنجاح', 'success')
    return redirect(url_for('auto_news', _anchor='sources'))

# حذف مصدر
@app.route('/sources/delete/<int:source_id>', methods=['POST'])
def delete_source(source_id):
    source = NewsSource.query.get_or_404(source_id)

    # حذف المصدر
    db.session.delete(source)
    db.session.commit()

    flash('تم حذف المصدر بنجاح', 'success')
    return redirect(url_for('auto_news', _anchor='sources'))

# التحقق من جاهزية المصادر
@app.route('/check-sources', methods=['POST'])
def check_sources():
    try:
        import requests
        import time
        from urllib.parse import urlparse
        import logging
        import urllib3
        from bs4 import BeautifulSoup
        import traceback
        import sys

        # تعطيل تحذيرات SSL
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # إعداد التسجيل
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)

        # تسجيل بداية التنفيذ
        logger.info("بدء تنفيذ وظيفة التحقق من جاهزية المصادر")

        # الحصول على جميع المصادر
        sources = NewsSource.query.all()

        if not sources:
            return jsonify({"results": [], "message": "لا توجد مصادر للتحقق منها"})

        results = []

        logger.info(f"عدد المصادر للتحقق: {len(sources)}")

        for i, source in enumerate(sources):
            logger.info(f"التحقق من المصدر {i+1}/{len(sources)}: {source.name} ({source.url})")
            start_time = time.time()
            is_ready = False
            can_fetch_news = False
            news_count = 0
            notes = ""

            try:
                # محاولة الاتصال بالمصدر
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                logger.info(f"محاولة الاتصال بالمصدر: {source.url}")

                # تجاهل التحقق من شهادة SSL
                response = requests.get(
                    source.url,
                    timeout=10,
                    headers=headers,
                    verify=False,
                    allow_redirects=True
                )

                # التحقق من نجاح الاتصال
                logger.info(f"تم الاتصال بالمصدر. رمز الحالة: {response.status_code}")

                if response.status_code == 200:
                    is_ready = True
                    logger.info("المصدر متاح (رمز الحالة 200)")

                    # محاولة استخراج الأخبار
                    try:
                        logger.info("محاولة استخراج الأخبار من المصدر")
                        # تحليل محتوى الصفحة
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # البحث عن الروابط
                        links = soup.find_all('a')
                        news_links = []

                        # تصفية الروابط للحصول على روابط الأخبار
                        for link in links:
                            href = link.get('href')
                            if href and (
                                'news' in href.lower() or
                                'article' in href.lower() or
                                'story' in href.lower() or
                                'خبر' in href or
                                'مقال' in href or
                                'تقرير' in href
                            ):
                                # تحويل الرابط النسبي إلى رابط مطلق
                                if href.startswith('/'):
                                    parsed_url = urlparse(source.url)
                                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                    href = base_url + href
                                elif not href.startswith(('http://', 'https://')):
                                    if source.url.endswith('/'):
                                        href = source.url + href
                                    else:
                                        href = source.url + '/' + href

                                news_links.append(href)

                        # إزالة الروابط المكررة
                        news_links = list(set(news_links))
                        logger.info(f"تم العثور على {len(news_links)} رابط أخبار فريد")

                        # التحقق من وجود روابط أخبار
                        if news_links:
                            can_fetch_news = True
                            news_count = len(news_links)
                            notes = f"تم الاتصال بنجاح وإمكانية جلب الأخبار متاحة ({news_count} رابط)"
                            logger.info(f"المصدر جاهز لجلب الأخبار. تم العثور على {news_count} رابط")
                        else:
                            notes = "تم الاتصال بنجاح ولكن لم يتم العثور على روابط أخبار"
                            logger.info("المصدر غير جاهز لجلب الأخبار. لم يتم العثور على روابط أخبار")
                    except Exception as e:
                        logger.error(f"خطأ عند استخراج الأخبار من المصدر {source.name}: {str(e)}")
                        notes = f"تم الاتصال بنجاح ولكن فشل استخراج الأخبار: {str(e)}"
                else:
                    notes = f"فشل الاتصال: رمز الحالة {response.status_code}"
            except requests.exceptions.Timeout:
                notes = "انتهت مهلة الاتصال"
            except requests.exceptions.ConnectionError:
                notes = "خطأ في الاتصال"
            except requests.exceptions.SSLError:
                notes = "خطأ في شهادة SSL"
            except requests.exceptions.InvalidURL:
                notes = "عنوان URL غير صالح"
            except Exception as e:
                logger.error(f"خطأ عند التحقق من المصدر {source.name}: {str(e)}")
                notes = f"خطأ: {str(e)}"

            # حساب الوقت المستغرق
            elapsed_time = int((time.time() - start_time) * 1000)  # بالمللي ثانية
            logger.info(f"الوقت المستغرق للتحقق: {elapsed_time} مللي ثانية")

            # تحديث حالة المصدر في قاعدة البيانات
            try:
                # التحقق من وجود الحقول
                if hasattr(source, 'can_fetch_news') and hasattr(source, 'news_count'):
                    old_can_fetch = getattr(source, 'can_fetch_news', False)
                    old_news_count = getattr(source, 'news_count', 0)

                    # تحديث الحقول
                    source.can_fetch_news = can_fetch_news
                    source.news_count = news_count

                    logger.info(f"تحديث حالة المصدر في قاعدة البيانات: can_fetch_news={can_fetch_news}, news_count={news_count}")

                    if old_can_fetch != can_fetch_news or old_news_count != news_count:
                        logger.info(f"تم تغيير حالة المصدر: can_fetch_news: {old_can_fetch} -> {can_fetch_news}, news_count: {old_news_count} -> {news_count}")
                else:
                    logger.warning(f"الحقول المطلوبة غير موجودة في نموذج المصدر: can_fetch_news={hasattr(source, 'can_fetch_news')}, news_count={hasattr(source, 'news_count')}")
                    logger.info(f"الحقول المتاحة في نموذج المصدر: {dir(source)}")
            except Exception as update_error:
                logger.error(f"خطأ أثناء تحديث حالة المصدر: {str(update_error)}")
                logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
                # لا نقوم برفع الخطأ هنا لتجنب فشل العملية بأكملها

            # إضافة النتيجة
            results.append({
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "is_ready": is_ready,
                "can_fetch_news": can_fetch_news,
                "news_count": news_count,
                "time_ms": elapsed_time,
                "notes": notes
            })

        # حفظ التغييرات في قاعدة البيانات
        try:
            logger.info("محاولة حفظ التغييرات في قاعدة البيانات")
            db.session.commit()
            logger.info("تم حفظ التغييرات بنجاح")
        except Exception as commit_error:
            logger.error(f"خطأ أثناء حفظ التغييرات: {str(commit_error)}")
            db.session.rollback()
            logger.info("تم التراجع عن التغييرات")
            raise commit_error

        logger.info(f"اكتمال التحقق من جاهزية المصادر. تم التحقق من {len(results)} مصدر")
        return jsonify({"results": results})
    except Exception as e:
        error_type = type(e).__name__
        error_traceback = traceback.format_exc()
        logger.error(f"خطأ في وظيفة التحقق من المصادر: {error_type}: {str(e)}")
        logger.error(f"تفاصيل الخطأ:\n{error_traceback}")

        # التراجع عن التغييرات في حالة حدوث خطأ
        try:
            db.session.rollback()
            logger.info("تم التراجع عن التغييرات بعد حدوث خطأ")
        except Exception as rollback_error:
            logger.error(f"خطأ أثناء التراجع عن التغييرات: {str(rollback_error)}")

        return jsonify({
            "error": str(e),
            "error_type": error_type,
            "traceback": error_traceback
        }), 500

# تحديث حالة المصادر
@app.route('/update-sources-status', methods=['POST'])
def update_sources_status():
    try:
        import requests
        import logging
        import urllib3
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        # تعطيل تحذيرات SSL
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # إعداد التسجيل
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # الحصول على جميع المصادر
        sources = NewsSource.query.all()

        if not sources:
            return jsonify({
                "success": True,
                "message": "لا توجد مصادر لتحديث حالتها",
                "updated_count": 0
            })

        updated_count = 0
        updated_sources = []

        for source in sources:
            try:
                # محاولة الاتصال بالمصدر
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(
                    source.url,
                    timeout=10,
                    headers=headers,
                    verify=False,
                    allow_redirects=True
                )

                # التحقق من نجاح الاتصال
                if response.status_code == 200:
                    # محاولة استخراج الأخبار
                    can_fetch_news = False
                    news_count = 0

                    try:
                        # تحليل محتوى الصفحة
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # البحث عن الروابط
                        links = soup.find_all('a')
                        news_links = []

                        # تصفية الروابط للحصول على روابط الأخبار
                        for link in links:
                            href = link.get('href')
                            if href and (
                                'news' in href.lower() or
                                'article' in href.lower() or
                                'story' in href.lower() or
                                'خبر' in href or
                                'مقال' in href or
                                'تقرير' in href
                            ):
                                # تحويل الرابط النسبي إلى رابط مطلق
                                if href.startswith('/'):
                                    parsed_url = urlparse(source.url)
                                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                    href = base_url + href
                                elif not href.startswith(('http://', 'https://')):
                                    if source.url.endswith('/'):
                                        href = source.url + href
                                    else:
                                        href = source.url + '/' + href

                                news_links.append(href)

                        # إزالة الروابط المكررة
                        news_links = list(set(news_links))

                        # التحقق من وجود روابط أخبار
                        if news_links:
                            can_fetch_news = True
                            news_count = len(news_links)
                    except Exception as e:
                        logger.error(f"خطأ عند استخراج الأخبار من المصدر {source.name}: {str(e)}")

                    # تحديث حالة المصدر
                    old_status = source.is_active
                    new_status = True  # المصدر متاح

                    # تحديث حقل can_fetch_news إذا كان موجودًا
                    if hasattr(source, 'can_fetch_news'):
                        old_can_fetch = source.can_fetch_news
                        source.can_fetch_news = can_fetch_news

                        if old_status != new_status or old_can_fetch != can_fetch_news:
                            source.is_active = new_status
                            updated_count += 1
                            updated_sources.append({
                                "id": source.id,
                                "name": source.name,
                                "old_status": old_status,
                                "new_status": new_status,
                                "can_fetch_news": can_fetch_news,
                                "news_count": news_count
                            })
                    else:
                        # إذا لم يكن الحقل موجودًا، نعتمد فقط على حالة الاتصال
                        if old_status != new_status:
                            source.is_active = new_status
                            updated_count += 1
                            updated_sources.append({
                                "id": source.id,
                                "name": source.name,
                                "old_status": old_status,
                                "new_status": new_status,
                                "can_fetch_news": can_fetch_news,
                                "news_count": news_count
                            })
                else:
                    # المصدر غير متاح
                    if source.is_active:
                        source.is_active = False
                        updated_count += 1
                        updated_sources.append({
                            "id": source.id,
                            "name": source.name,
                            "old_status": True,
                            "new_status": False,
                            "error": f"رمز الحالة {response.status_code}"
                        })
            except requests.exceptions.RequestException as e:
                # في حالة حدوث خطأ، تعيين المصدر كغير نشط
                logger.error(f"خطأ عند الاتصال بالمصدر {source.name}: {str(e)}")
                if source.is_active:
                    source.is_active = False
                    updated_count += 1
                    updated_sources.append({
                        "id": source.id,
                        "name": source.name,
                        "old_status": True,
                        "new_status": False,
                        "error": str(e)
                    })
            except Exception as e:
                logger.error(f"خطأ غير متوقع عند تحديث حالة المصدر {source.name}: {str(e)}")

        # حفظ التغييرات
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"تم تحديث حالة {updated_count} مصدر",
            "updated_count": updated_count,
            "updated_sources": updated_sources
        })
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logging.error(f"خطأ في وظيفة تحديث حالة المصادر: {str(e)}\n{error_traceback}")

        # التراجع عن التغييرات في حالة حدوث خطأ
        db.session.rollback()

        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_traceback
        }), 500

# الحصول على قائمة المصادر غير الفعالة
@app.route('/get-inactive-sources', methods=['GET'])
def get_inactive_sources():
    try:
        import logging

        # إعداد التسجيل
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # الحصول على جميع المصادر غير الفعالة
        inactive_sources = NewsSource.query.filter_by(is_active=False).all()

        # تحويل المصادر إلى قائمة
        sources_list = [{
            "id": source.id,
            "name": source.name,
            "url": source.url
        } for source in inactive_sources]

        return jsonify({
            "success": True,
            "inactive_sources": sources_list,
            "count": len(sources_list)
        })
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logging.error(f"خطأ في وظيفة الحصول على قائمة المصادر غير الفعالة: {str(e)}\n{error_traceback}")

        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_traceback
        }), 500

# حذف المصادر غير الفعالة
@app.route('/delete-inactive-sources', methods=['POST'])
def delete_inactive_sources():
    try:
        import logging

        # إعداد التسجيل
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # الحصول على جميع المصادر غير الفعالة
        inactive_sources = NewsSource.query.filter_by(is_active=False).all()

        if not inactive_sources:
            flash('لا توجد مصادر غير فعالة للحذف', 'info')
            return redirect(url_for('auto_news', _anchor='sources'))

        # حساب عدد المصادر
        count = len(inactive_sources)

        # حفظ أسماء المصادر للتسجيل
        source_names = [source.name for source in inactive_sources]

        # حذف المصادر
        for source in inactive_sources:
            db.session.delete(source)

        # حفظ التغييرات
        db.session.commit()

        # تسجيل العملية
        logger.info(f"تم حذف {count} مصدر غير فعال: {', '.join(source_names)}")

        flash(f'تم حذف {count} مصدر غير فعال بنجاح', 'success')
        return redirect(url_for('auto_news', _anchor='sources'))
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logging.error(f"خطأ في وظيفة حذف المصادر غير الفعالة: {str(e)}\n{error_traceback}")

        # التراجع عن التغييرات في حالة حدوث خطأ
        db.session.rollback()

        flash(f'حدث خطأ أثناء حذف المصادر غير الفعالة: {str(e)}', 'danger')
        return redirect(url_for('auto_news', _anchor='sources'))

# تم إزالة وظيفة جلب الأخبار من جميع المصادر

# تم إزالة وظيفة تشغيل المجدول يدويًا

# تم إزالة وظيفة جلب الأخبار من مصدر محدد

# تم إزالة وظيفة حفظ الأخبار المستخرجة

# تم إزالة وظيفة عرض سجلات الجلب

# صفحة الجلب الآلي للأخبار الموحدة
@app.route('/auto-news')
def auto_news():
    # جلب الأخبار المجلوبة تلقائيًا (قبل الاعتماد)
    from app.models.relational_models import ScrapedNews, NewsSource, Category, Governorate
    from datetime import datetime

    # الحصول على معلمات الفلترة
    source_filter = request.args.get('source', '')

    # جلب الأخبار المجلوبة تلقائيًا (التي لم يتم حفظها بعد)
    query = ScrapedNews.query.filter_by(is_saved=False)

    # تطبيق الفلترة حسب المصدر إذا تم تحديده
    if source_filter:
        query = query.filter(ScrapedNews.source == source_filter)

    # ترتيب الأخبار حسب تاريخ الإنشاء تنازليًا
    auto_news = query.order_by(ScrapedNews.created_at.desc()).all()

    # جلب مصادر الأخبار
    sources = NewsSource.query.all()

    # جلب التصنيفات
    categories = Category.query.all()

    # جلب المحافظات
    governorates = Governorate.query.all()

    # الوقت الحالي
    now = datetime.now()

    # الحصول على إحصائيات آخر عملية جلب
    fetch_stats = {
        'total_fetched': session.get('total_fetched', 0),
        'fetch_time': session.get('fetch_time', ''),
        'last_fetch_time': session.get('last_fetch_time', ''),
        'source_stats': session.get('source_stats', {}),
        'fetch_results': session.get('fetch_results', [])
    }

    # إحصائيات المصادر الحالية
    current_sources_stats = {}
    all_news = ScrapedNews.query.filter_by(is_saved=False).all()
    for news in all_news:
        if news.source not in current_sources_stats:
            current_sources_stats[news.source] = 0
        current_sources_stats[news.source] += 1

    # ترتيب المصادر حسب عدد الأخبار
    sorted_sources_stats = sorted(current_sources_stats.items(), key=lambda x: x[1], reverse=True)

    return render_template('auto_news_unified.html',
                          auto_news=auto_news,
                          sources=sources,
                          categories=categories,
                          governorates=governorates,
                          now=now,
                          fetch_stats=fetch_stats,
                          current_sources_stats=sorted_sources_stats,
                          source_filter=source_filter)

# إعادة توجيه الصفحة القديمة إلى الصفحة الجديدة
@app.route('/auto-fetch')
def auto_fetch():
    return redirect(url_for('auto_news'))

# تنظيف صفحة الأخبار التلقائية (حذف جميع الأخبار المجلوبة تلقائيًا التي لم يتم حفظها)
@app.route('/clean-auto-news', methods=['POST'])
def clean_auto_news():
    from app.models.relational_models import ScrapedNews

    try:
        # حذف جميع الأخبار المجلوبة تلقائيًا التي لم يتم حفظها
        count = ScrapedNews.query.filter_by(is_saved=False).delete()

        # حفظ التغييرات
        db.session.commit()

        # إرسال رسالة نجاح
        flash(f'تم تنظيف صفحة الأخبار التلقائية بنجاح. تم حذف {count} خبر.', 'success')

    except Exception as e:
        # إرسال رسالة خطأ
        flash(f'حدث خطأ أثناء تنظيف صفحة الأخبار التلقائية: {str(e)}', 'danger')
        db.session.rollback()

    # العودة إلى صفحة الأخبار التلقائية
    return redirect(url_for('auto_news'))

# جلب الأخبار من المصادر
@app.route('/fetch-news-now', methods=['POST'])
def fetch_news_now():
    from app.models.relational_models import ScrapedNews, NewsSource
    from app.utils.news_fetcher import NewsFetcher
    from datetime import date
    import time
    import logging

    # إعداد التسجيل
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    try:
        # تسجيل بداية عملية جلب الأخبار
        logger.info("بدء عملية جلب الأخبار التلقائي")
        start_time = time.time()

        # إنشاء كائن جالب الأخبار
        with app.app_context():
            fetcher = NewsFetcher(db, ScrapedNews, NewsSource)

            # جلب الأخبار من جميع المصادر النشطة (زيادة عدد الأخبار لكل مصدر)
            results = fetcher.fetch_all_sources(max_news_per_source=50)

            # حساب إجمالي الأخبار التي تم جلبها
            total_fetched = sum(result['count'] for result in results)

            # حساب الوقت المستغرق
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)

            # تسجيل نتائج عملية جلب الأخبار
            logger.info(f"اكتمال عملية جلب الأخبار. تم جلب {total_fetched} خبر في {minutes} دقيقة و {seconds} ثانية")

            # تخزين إحصائيات المصادر في الجلسة
            source_stats = {}
            for result in results:
                source_name = result['source']
                source_stats[source_name] = {
                    'count': result['count'],
                    'status': result['status']
                }
                if 'error' in result:
                    source_stats[source_name]['error'] = result['error']

            # تخزين الإحصائيات في الجلسة
            session['source_stats'] = source_stats
            session['total_fetched'] = total_fetched
            session['fetch_time'] = f"{minutes} دقيقة و {seconds} ثانية"
            session['last_fetch_time'] = time.strftime("%Y-%m-%d %H:%M:%S")
            session['fetch_results'] = results

            # إرسال رسالة نجاح
            if total_fetched > 0:
                today = date.today().strftime('%Y-%m-%d')
                flash(f'تم جلب {total_fetched} خبر عن العراق بتاريخ اليوم ({today}) بنجاح في {minutes} دقيقة و {seconds} ثانية من {len(results)} مصدر', 'success')
            else:
                flash('لم يتم العثور على أخبار جديدة عن العراق بتاريخ اليوم. قد تكون جميع الأخبار موجودة مسبقًا أو قد تكون هناك مشكلة في الاتصال بالمصادر.', 'warning')

    except Exception as e:
        import traceback
        logger.error(f"خطأ في عملية جلب الأخبار: {str(e)}\n{traceback.format_exc()}")
        flash(f'حدث خطأ أثناء جلب الأخبار: {str(e)}', 'danger')

    # العودة إلى صفحة الجلب الآلي
    return redirect(url_for('auto_news'))

# حفظ خبر مجلوب تلقائيًا في جدول الأخبار المعتمدة
@app.route('/save-scraped-news/<int:news_id>', methods=['POST'])
def save_scraped_news(news_id):
    from app.models.relational_models import ScrapedNews

    # جلب الخبر المجلوب
    scraped_news = ScrapedNews.query.get_or_404(news_id)

    # التحقق من أن الخبر لم يتم حفظه من قبل
    if scraped_news.is_saved:
        flash('تم حفظ هذا الخبر مسبقًا', 'warning')
        return redirect(url_for('auto_news'))

    # الحصول على التصنيف والمحافظة من النموذج
    category_id = request.form.get('category_id')
    governorate_id = request.form.get('governorate_id')

    if not category_id or not governorate_id:
        flash('يرجى تحديد التصنيف والمحافظة', 'danger')
        return redirect(url_for('auto_news'))

    # إنشاء خبر جديد في جدول الأخبار المعتمدة
    news = News(
        title=scraped_news.title,
        content=scraped_news.content,
        date=scraped_news.date,
        source=scraped_news.source,
        source_url=scraped_news.source_url,
        category_id=category_id,
        governorate_id=governorate_id,
        content_hash=scraped_news.content_hash
    )

    # تحديث حالة الخبر المجلوب
    scraped_news.is_saved = True

    # حفظ التغييرات
    db.session.add(news)
    db.session.commit()

    flash('تم حفظ الخبر بنجاح', 'success')
    return redirect(url_for('auto_news'))


# صفحة الإعدادات
@app.route('/settings')
def settings():
    # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجوداً
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # الحصول على قائمة النسخ الاحتياطية
    backups = []

    # التحقق من وجود المجلد وإمكانية الوصول إليه
    if os.path.exists(backup_dir) and os.access(backup_dir, os.R_OK):
        for filename in os.listdir(backup_dir):
            if filename.endswith(('.sqlite', '.db', '.backup')):
                file_path = os.path.join(backup_dir, filename)
                file_size = os.path.getsize(file_path)
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                # تحويل حجم الملف إلى صيغة مقروءة
                if file_size < 1024:
                    size_str = f"{file_size} بايت"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} كيلوبايت"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} ميجابايت"

                backups.append({
                    'filename': filename,
                    'size': size_str,
                    'date': file_date,
                    'path': file_path
                })

    # ترتيب النسخ الاحتياطية حسب التاريخ (الأحدث أولاً)
    backups.sort(key=lambda x: x['date'], reverse=True)

    return render_template('settings.html', backups=backups)

# إنشاء نسخة احتياطية
@app.route('/backup/create', methods=['POST'])
def create_backup():
    try:
        # الحصول على مسار قاعدة البيانات الحالية
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']

        # طباعة مسار قاعدة البيانات للتصحيح
        print(f"Database URI: {db_uri}")

        # التعامل مع مسارات قاعدة البيانات المختلفة
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            # إذا كان المسار نسبيًا، قم بتحويله إلى مسار مطلق
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        else:
            flash('نوع قاعدة البيانات غير مدعوم للنسخ الاحتياطي', 'danger')
            return redirect(url_for('settings'))

        # التحقق من وجود ملف قاعدة البيانات
        if not os.path.exists(db_path):
            flash(f'ملف قاعدة البيانات غير موجود في المسار: {db_path}', 'danger')
            return redirect(url_for('settings'))

        # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجوداً
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # إنشاء اسم ملف النسخة الاحتياطية بالتاريخ والوقت
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.sqlite"
        backup_path = os.path.join(backup_dir, backup_filename)

        # نسخ ملف قاعدة البيانات
        shutil.copy2(db_path, backup_path)

        flash('تم إنشاء نسخة احتياطية بنجاح', 'success')
    except Exception as e:
        flash(f'حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}', 'danger')
        # طباعة تفاصيل الخطأ للتصحيح
        import traceback
        print(traceback.format_exc())

    return redirect(url_for('settings'))

# تنزيل نسخة احتياطية
@app.route('/backup/download/<filename>')
def download_backup(filename):
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if not os.path.exists(backup_path):
        flash('النسخة الاحتياطية غير موجودة', 'warning')
        return redirect(url_for('settings'))

    return send_file(backup_path, as_attachment=True)

# حذف نسخة احتياطية
@app.route('/backup/delete/<filename>')
def delete_backup(filename):
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        backup_path = os.path.join(backup_dir, filename)

        if os.path.exists(backup_path):
            os.remove(backup_path)
            flash('تم حذف النسخة الاحتياطية بنجاح', 'success')
        else:
            flash('النسخة الاحتياطية غير موجودة', 'warning')
    except Exception as e:
        flash(f'حدث خطأ أثناء حذف النسخة الاحتياطية: {str(e)}', 'danger')
        # طباعة تفاصيل الخطأ للتصحيح
        import traceback
        print(traceback.format_exc())

    return redirect(url_for('settings'))

# استعادة نسخة احتياطية
@app.route('/backup/restore/<filename>')
def restore_backup(filename):
    try:
        # الحصول على مسار قاعدة البيانات الحالية
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']

        # طباعة مسار قاعدة البيانات للتصحيح
        print(f"Database URI: {db_uri}")

        # التعامل مع مسارات قاعدة البيانات المختلفة
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            # إذا كان المسار نسبيًا، قم بتحويله إلى مسار مطلق
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        else:
            flash('نوع قاعدة البيانات غير مدعوم للاستعادة', 'danger')
            return redirect(url_for('settings'))

        # مسار النسخة الاحتياطية
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        backup_path = os.path.join(backup_dir, filename)

        if not os.path.exists(backup_path):
            flash('النسخة الاحتياطية غير موجودة', 'warning')
            return redirect(url_for('settings'))

        # التحقق من صحة ملف النسخة الاحتياطية
        try:
            conn = sqlite3.connect(backup_path)
            conn.close()
        except sqlite3.Error:
            flash('ملف النسخة الاحتياطية ليس قاعدة بيانات SQLite صالحة', 'danger')
            return redirect(url_for('settings'))

        # إغلاق اتصالات قاعدة البيانات
        db.session.close()
        db.engine.dispose()

        # عمل نسخة احتياطية من قاعدة البيانات الحالية قبل الاستعادة
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup_filename = f"pre_restore_backup_{timestamp}.sqlite"
        current_backup_path = os.path.join(backup_dir, current_backup_filename)

        # نسخ قاعدة البيانات الحالية
        shutil.copy2(db_path, current_backup_path)

        # استعادة النسخة الاحتياطية
        shutil.copy2(backup_path, db_path)

        flash('تم استعادة النسخة الاحتياطية بنجاح. يرجى إعادة تشغيل التطبيق لتطبيق التغييرات.', 'success')
    except Exception as e:
        flash(f'حدث خطأ أثناء استعادة النسخة الاحتياطية: {str(e)}', 'danger')
        # طباعة تفاصيل الخطأ للتصحيح
        import traceback
        print(traceback.format_exc())

    return redirect(url_for('settings'))

# استعادة نسخة احتياطية من ملف مرفوع
@app.route('/backup/restore/upload', methods=['POST'])
def restore_backup_upload():
    try:
        if 'backup_file' not in request.files:
            flash('لم يتم تحديد ملف', 'warning')
            return redirect(url_for('settings'))

        backup_file = request.files['backup_file']

        if backup_file.filename == '':
            flash('لم يتم تحديد ملف', 'warning')
            return redirect(url_for('settings'))

        if not (backup_file.filename.endswith('.sqlite') or
                backup_file.filename.endswith('.db') or
                backup_file.filename.endswith('.backup')):
            flash('صيغة الملف غير صالحة. يجب أن يكون الملف بصيغة .sqlite أو .db أو .backup', 'warning')
            return redirect(url_for('settings'))

        # الحصول على مسار قاعدة البيانات الحالية
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']

        # طباعة مسار قاعدة البيانات للتصحيح
        print(f"Database URI: {db_uri}")

        # التعامل مع مسارات قاعدة البيانات المختلفة
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            # إذا كان المسار نسبيًا، قم بتحويله إلى مسار مطلق
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        else:
            flash('نوع قاعدة البيانات غير مدعوم للاستعادة', 'danger')
            return redirect(url_for('settings'))

        # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجوداً
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # إغلاق اتصالات قاعدة البيانات
        db.session.close()
        db.engine.dispose()

        # عمل نسخة احتياطية من قاعدة البيانات الحالية قبل الاستعادة
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_backup_filename = f"pre_restore_backup_{timestamp}.sqlite"
        current_backup_path = os.path.join(backup_dir, current_backup_filename)

        # نسخ قاعدة البيانات الحالية
        shutil.copy2(db_path, current_backup_path)

        # حفظ الملف المرفوع مؤقتاً
        uploaded_filename = secure_filename(backup_file.filename)
        uploaded_path = os.path.join(backup_dir, f"uploaded_{timestamp}_{uploaded_filename}")
        backup_file.save(uploaded_path)

        # التحقق من صحة ملف قاعدة البيانات
        try:
            conn = sqlite3.connect(uploaded_path)
            conn.close()
        except sqlite3.Error:
            os.remove(uploaded_path)
            flash('الملف المرفوع ليس قاعدة بيانات SQLite صالحة', 'danger')
            return redirect(url_for('settings'))

        # استعادة النسخة الاحتياطية
        shutil.copy2(uploaded_path, db_path)

        # حفظ الملف المرفوع في مجلد النسخ الاحتياطية
        saved_backup_filename = f"uploaded_backup_{timestamp}_{uploaded_filename}"
        saved_backup_path = os.path.join(backup_dir, saved_backup_filename)
        shutil.copy2(uploaded_path, saved_backup_path)

        # حذف الملف المؤقت
        os.remove(uploaded_path)

        flash('تم استعادة النسخة الاحتياطية بنجاح. يرجى إعادة تشغيل التطبيق لتطبيق التغييرات.', 'success')
    except Exception as e:
        flash(f'حدث خطأ أثناء استعادة النسخة الاحتياطية: {str(e)}', 'danger')
        # طباعة تفاصيل الخطأ للتصحيح
        import traceback
        print(traceback.format_exc())

    return redirect(url_for('settings'))

# صفحة الإحصائيات
@app.route('/statistics')
def statistics():
    print("بدء تنفيذ دالة الإحصائيات")
    try:
        # إحصائيات عامة
        total_news = News.query.count()
        total_categories = Category.query.count()
        total_governorates = Governorate.query.count()
        total_sources = db.session.query(News.source).distinct().count()

        # إحصائيات الأخبار حسب التصنيف
        category_stats = []
        categories_list = Category.query.all()
        for cat in categories_list:
            news_count = News.query.filter_by(category_id=cat.id).count()
            if news_count > 0:
                category_stats.append({
                    'id': cat.id,
                    'name': cat.name,
                    'news_count': news_count
                })
        # ترتيب التصنيفات حسب عدد الأخبار تنازلياً
        category_stats = sorted(category_stats, key=lambda x: x['news_count'], reverse=True)

        # إحصائيات الأخبار حسب المحافظة
        governorate_stats = []
        governorates_list = Governorate.query.all()
        for gov in governorates_list:
            news_count = News.query.filter_by(governorate_id=gov.id).count()
            if news_count > 0:
                governorate_stats.append({
                    'id': gov.id,
                    'name': gov.name,
                    'news_count': news_count
                })
        # ترتيب المحافظات حسب عدد الأخبار تنازلياً
        governorate_stats = sorted(governorate_stats, key=lambda x: x['news_count'], reverse=True)

        # إحصائيات الأخبار حسب المصدر
        source_counts = {}
        all_news = News.query.all()
        for news in all_news:
            if news.source in source_counts:
                source_counts[news.source] += 1
            else:
                source_counts[news.source] = 1

        # تحويل القاموس إلى قائمة وترتيبها تنازلياً
        source_stats = []
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            source_stats.append({
                'source': source,
                'news_count': count
            })

        # إحصائيات الأخبار حسب التاريخ (آخر 30 يوم)
        thirty_days_ago = date.today() - timedelta(days=30)
        date_stats = []
        date_counts = {}
        recent_news = News.query.filter(News.date >= thirty_days_ago).all()
        for news in recent_news:
            date_str = news.date.strftime('%Y-%m-%d')
            if date_str in date_counts:
                date_counts[date_str] += 1
            else:
                date_counts[date_str] = 1

        # تحويل القاموس إلى قائمة وترتيبها تنازلياً حسب التاريخ
        for date_str, count in sorted(date_counts.items(), reverse=True):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            date_stats.append({
                'date': date_obj,
                'news_count': count
            })

        # إحصائيات الحقول الديناميكية لكل تصنيف
        field_stats = []

        # الحصول على جميع الأخبار مع التصنيفات والحقول الديناميكية
        all_news = News.query.all()
        print(f"عدد الأخبار: {len(all_news)}")

        # إنشاء قاموس لتجميع البيانات حسب التصنيف
        category_data = {}

        # تجميع البيانات من جميع الأخبار
        for news in all_news:
            if news.category_id not in category_data:
                category = Category.query.get(news.category_id)
                if not category:
                    continue

                category_data[news.category_id] = {
                    'category_id': news.category_id,
                    'category_name': category.name,
                    'news_count': 0,
                    'fields': {}
                }

            # زيادة عدد الأخبار لهذا التصنيف
            category_data[news.category_id]['news_count'] += 1

            # الحصول على قيم الحقول الديناميكية لهذا الخبر
            field_values = FieldValue.query.filter_by(news_id=news.id).all()
            print(f"الخبر ID: {news.id}, عدد قيم الحقول: {len(field_values)}")

            for fv in field_values:
                field = Field.query.get(fv.field_id)
                if not field:
                    print(f"لم يتم العثور على الحقل ID: {fv.field_id}")
                    continue

                if fv.field_id not in category_data[news.category_id]['fields']:
                    category_data[news.category_id]['fields'][fv.field_id] = {
                        'id': fv.field_id,
                        'name': field.name,
                        'field_type': field.field_type,
                        'total': 0,
                        'values': {}
                    }

                # إضافة القيمة إلى قاموس القيم
                if fv.value not in category_data[news.category_id]['fields'][fv.field_id]['values']:
                    category_data[news.category_id]['fields'][fv.field_id]['values'][fv.value] = 0

                category_data[news.category_id]['fields'][fv.field_id]['values'][fv.value] += 1

                # إذا كان الحقل رقمي، نقوم بجمع القيم
                if field.field_type == 'number' and fv.value.isdigit():
                    category_data[news.category_id]['fields'][fv.field_id]['total'] += int(fv.value)

        # تحويل البيانات إلى الصيغة المطلوبة للعرض
        for category_id, data in category_data.items():
            field_data = []

            for field_id, field_info in data['fields'].items():
                # تحويل قاموس القيم إلى قائمة
                values_list = []
                for value, count in sorted(field_info['values'].items(), key=lambda x: x[1], reverse=True):
                    values_list.append({
                        'value': value,
                        'value_count': count
                    })

                # إضافة الحقل مع قائمة القيم
                field_data.append({
                    'id': field_info['id'],
                    'name': field_info['name'],
                    'field_type': field_info['field_type'],
                    'total': field_info['total'],
                    'value_items': values_list
                })

            # إضافة التصنيف مع قائمة الحقول
            field_stats.append({
                'category_id': data['category_id'],
                'category_name': data['category_name'],
                'news_count': data['news_count'],
                'fields': field_data
            })

        print(f"عدد التصنيفات في الإحصائيات: {len(field_stats)}")

        # إحصائيات الأخبار حسب الشهر والسنة
        month_stats = []
        month_counts = {}
        for news in all_news:
            month_key = f"{news.date.year}-{news.date.month:02d}"
            if month_key in month_counts:
                month_counts[month_key] += 1
            else:
                month_counts[month_key] = 1

        # تحويل القاموس إلى قائمة وترتيبها تنازلياً
        for month, count in sorted(month_counts.items(), reverse=True)[:12]:
            month_stats.append({
                'month': month,
                'news_count': count
            })
    except Exception as e:
        import traceback
        print(f"خطأ في صفحة الإحصائيات: {str(e)}")
        print(traceback.format_exc())
        # إرجاع قيم افتراضية في حالة حدوث خطأ
        total_news = 0
        total_categories = 0
        total_governorates = 0
        total_sources = 0
        category_stats = []
        governorate_stats = []
        source_stats = []
        date_stats = []
        field_stats = []
        month_stats = []

    return render_template('statistics.html',
                          total_news=total_news,
                          total_categories=total_categories,
                          total_governorates=total_governorates,
                          total_sources=total_sources,
                          category_stats=category_stats,
                          governorate_stats=governorate_stats,
                          source_stats=source_stats,
                          date_stats=date_stats,
                          field_stats=field_stats,
                          month_stats=month_stats)

# صفحة طباعة إحصائيات الحقول الديناميكية
@app.route('/stats')
def print_statistics():
    try:
        # الحصول على التاريخ الحالي بالعربية
        today = date.today()
        arabic_months = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        arabic_days = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        day_name = arabic_days[today.weekday()]
        today_date = f"{day_name} {today.day} {arabic_months[today.month]} {today.year}"

        # إحصائيات الحقول الديناميكية لكل تصنيف
        field_stats = []

        # الحصول على جميع الأخبار مع التصنيفات والحقول الديناميكية
        all_news = News.query.all()

        # إنشاء قاموس لتجميع البيانات حسب التصنيف
        category_data = {}

        # تجميع البيانات من جميع الأخبار
        for news in all_news:
            if news.category_id not in category_data:
                category = Category.query.get(news.category_id)
                if not category:
                    continue

                category_data[news.category_id] = {
                    'category_id': news.category_id,
                    'category_name': category.name,
                    'news_count': 0,
                    'fields': {}
                }

            # زيادة عدد الأخبار لهذا التصنيف
            category_data[news.category_id]['news_count'] += 1

            # الحصول على قيم الحقول الديناميكية لهذا الخبر
            field_values = FieldValue.query.filter_by(news_id=news.id).all()

            for fv in field_values:
                field = Field.query.get(fv.field_id)
                if not field:
                    continue

                if fv.field_id not in category_data[news.category_id]['fields']:
                    category_data[news.category_id]['fields'][fv.field_id] = {
                        'id': fv.field_id,
                        'name': field.name,
                        'field_type': field.field_type,
                        'total': 0,
                        'values': {}
                    }

                # إضافة القيمة إلى قاموس القيم
                if fv.value not in category_data[news.category_id]['fields'][fv.field_id]['values']:
                    category_data[news.category_id]['fields'][fv.field_id]['values'][fv.value] = 0

                category_data[news.category_id]['fields'][fv.field_id]['values'][fv.value] += 1

                # إذا كان الحقل رقمي، نقوم بجمع القيم
                if field.field_type == 'number' and fv.value.isdigit():
                    category_data[news.category_id]['fields'][fv.field_id]['total'] += int(fv.value)

        # تحويل البيانات إلى الصيغة المطلوبة للعرض
        for category_id, data in category_data.items():
            field_data = []

            for field_id, field_info in data['fields'].items():
                # تحويل قاموس القيم إلى قائمة
                values_list = []
                for value, count in sorted(field_info['values'].items(), key=lambda x: x[1], reverse=True):
                    values_list.append({
                        'value': value,
                        'value_count': count
                    })

                # إضافة الحقل مع قائمة القيم
                field_data.append({
                    'id': field_info['id'],
                    'name': field_info['name'],
                    'field_type': field_info['field_type'],
                    'total': field_info['total'],
                    'value_items': values_list
                })

            # إضافة التصنيف مع قائمة الحقول
            field_stats.append({
                'category_id': data['category_id'],
                'category_name': data['category_name'],
                'news_count': data['news_count'],
                'fields': field_data
            })

        # إضافة عنوان الصفحة بدون الزوائد
        response = make_response(render_template('print_statistics.html',
                                field_stats=field_stats,
                                today_date=today_date))
        # إضافة رؤوس HTTP لمنع إظهار الزوائد في عنوان الصفحة
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"خطأ في صفحة طباعة الإحصائيات: {str(e)}")
        flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('statistics'))

if __name__ == '__main__':
    app.run(debug=True)
