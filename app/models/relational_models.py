from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
import json
from enum import Enum

db = SQLAlchemy()

# تعريف أنواع مصادر الأخبار
class SourceType(Enum):
    WEBSITE = 'website'
    RSS = 'rss'
    API = 'api'

# جدول المحافظات
class Governorate(db.Model):
    """محافظات العراق ماعدا إقليم كردستان"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    news = db.relationship('News', backref='governorate', lazy='dynamic')

    def __repr__(self):
        return f'<Governorate {self.name}>'

# جدول التصنيفات
class Category(db.Model):
    """تصنيفات الأخبار"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # العلاقات
    news = db.relationship('News', backref='category', lazy='dynamic')
    fields = db.relationship('Field', backref='category', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Category {self.name}>'

# جدول الحقول الديناميكية
class Field(db.Model):
    """الحقول الديناميكية للتصنيفات"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    field_type = db.Column(db.String(20), nullable=False)  # text, textarea, number, date, select
    options = db.Column(db.Text, nullable=True)  # JSON string for select options
    required = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)  # ترتيب الحقل في النموذج

    # العلاقات
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    field_values = db.relationship('FieldValue', backref='field', lazy='dynamic', cascade='all, delete-orphan')

    def get_options(self):
        """استرجاع خيارات القائمة المنسدلة كقائمة"""
        if self.options:
            return json.loads(self.options)
        return []

    def set_options(self, options_list):
        """تعيين خيارات القائمة المنسدلة من قائمة"""
        self.options = json.dumps(options_list)

    def __repr__(self):
        return f'<Field {self.name} ({self.field_type})>'

# جدول الأخبار
class News(db.Model):
    """الأخبار"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    source = db.Column(db.String(200), nullable=False)
    source_url = db.Column(db.String(500), nullable=True)
    content_hash = db.Column(db.String(32), nullable=True, index=True)  # بصمة المحتوى (MD5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    governorate_id = db.Column(db.Integer, db.ForeignKey('governorate.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    field_values = db.relationship('FieldValue', backref='news', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<News {self.title}>'

# جدول قيم الحقول الديناميكية
class FieldValue(db.Model):
    """قيم الحقول الديناميكية للأخبار"""
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Text, nullable=True)

    # العلاقات
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'), nullable=False)

    def __repr__(self):
        return f'<FieldValue {self.field_id}:{self.value}>'

# تهيئة قاعدة البيانات بمحافظات العراق
def init_governorates(db_session):
    governorates = [
        'بغداد', 'البصرة', 'نينوى', 'أربيل', 'النجف', 'كربلاء', 'ذي قار', 'الأنبار',
        'ديالى', 'واسط', 'ميسان', 'المثنى', 'صلاح الدين', 'بابل', 'القادسية'
    ]

    for gov_name in governorates:
        if not Governorate.query.filter_by(name=gov_name).first():
            gov = Governorate(name=gov_name)
            db_session.add(gov)

    db_session.commit()

# ترحيل البيانات من النموذج القديم إلى النموذج الجديد
def migrate_from_old_model(db_session, old_categories):
    """
    ترحيل البيانات من نموذج قاعدة البيانات القديم إلى النموذج الجديد

    :param db_session: جلسة قاعدة البيانات
    :param old_categories: قائمة التصنيفات القديمة
    """
    for old_category in old_categories:
        # إنشاء تصنيف جديد
        new_category = Category(name=old_category.name)
        db_session.add(new_category)
        db_session.flush()  # للحصول على معرف التصنيف الجديد

        # استرجاع الحقول الديناميكية من التصنيف القديم
        dynamic_fields = old_category.get_dynamic_fields()

        # إنشاء حقول ديناميكية جديدة
        for i, field_data in enumerate(dynamic_fields):
            field = Field(
                name=field_data.get('name', 'حقل بدون اسم'),
                field_type=field_data.get('type', 'text'),
                category_id=new_category.id,
                order=i
            )

            # إضافة الخيارات إذا كان نوع الحقل قائمة منسدلة
            if field.field_type == 'select' and 'options' in field_data:
                field.set_options(field_data['options'])

            db_session.add(field)

    db_session.commit()
    print(f"تم ترحيل {len(old_categories)} تصنيف بنجاح.")

# جدول مصادر الأخبار
class NewsSource(db.Model):
    """مصادر الأخبار"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    source_type = db.Column(db.String(20), nullable=False, default=SourceType.WEBSITE.value)
    is_active = db.Column(db.Boolean, default=True)

    # معلومات إضافية
    is_iraqi = db.Column(db.Boolean, default=False)  # هل المصدر عراقي
    can_fetch_news = db.Column(db.Boolean, default=False)  # هل يمكن جلب الأخبار من المصدر
    news_count = db.Column(db.Integer, default=0)  # عدد الأخبار التي يمكن جلبها من المصدر

    # إعدادات إضافية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<NewsSource {self.name}>'

    def get_keywords(self):
        """استرجاع الكلمات المفتاحية كقائمة"""
        return []

    def set_keywords(self, keywords_list):
        """تعيين الكلمات المفتاحية من قائمة"""
        pass

# جدول الأخبار المجلوبة تلقائيًا (قبل الاعتماد)
class ScrapedNews(db.Model):
    """الأخبار المجلوبة تلقائيًا قبل اعتمادها"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    source = db.Column(db.String(100), nullable=False)  # اسم المصدر
    source_url = db.Column(db.String(500), nullable=True)  # رابط المصدر
    content_hash = db.Column(db.String(32), nullable=True, unique=True)  # بصمة المحتوى لمنع التكرار

    # معلومات إضافية
    is_saved = db.Column(db.Boolean, default=False)  # هل تم حفظ الخبر في جدول الأخبار المعتمدة
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    source_id = db.Column(db.Integer, db.ForeignKey('news_source.id'), nullable=True)
    news_source = db.relationship('NewsSource', backref=db.backref('scraped_news', lazy=True))

    def __repr__(self):
        return f'<ScrapedNews {self.title}>'

    def get_keywords(self):
        """استرجاع الكلمات المفتاحية كقائمة"""
        return []

    def set_keywords(self, keywords_list):
        """تعيين الكلمات المفتاحية من قائمة"""
        pass

# تم إزالة جدول سجل الجلب
