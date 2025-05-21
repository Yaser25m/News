from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

class Governorate(db.Model):
    """محافظات العراق ماعدا إقليم كردستان"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    news = db.relationship('News', backref='governorate', lazy='dynamic')

    def __repr__(self):
        return f'<Governorate {self.name}>'

class Category(db.Model):
    """تصنيفات الأخبار"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    dynamic_fields = db.Column(db.Text, nullable=True)  # JSON string of field definitions
    news = db.relationship('News', backref='category', lazy='dynamic')
    
    def get_dynamic_fields(self):
        """استرجاع الحقول الديناميكية كقائمة"""
        if self.dynamic_fields:
            return json.loads(self.dynamic_fields)
        return []
    
    def set_dynamic_fields(self, fields_list):
        """تعيين الحقول الديناميكية من قائمة"""
        self.dynamic_fields = json.dumps(fields_list)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class News(db.Model):
    """الأخبار"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    source = db.Column(db.String(200), nullable=False)
    source_url = db.Column(db.String(500), nullable=True)
    governorate_id = db.Column(db.Integer, db.ForeignKey('governorate.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    dynamic_data = db.Column(db.Text, nullable=True)  # JSON string of dynamic field values
    
    def get_dynamic_data(self):
        """استرجاع بيانات الحقول الديناميكية كقاموس"""
        if self.dynamic_data:
            return json.loads(self.dynamic_data)
        return {}
    
    def set_dynamic_data(self, data_dict):
        """تعيين بيانات الحقول الديناميكية من قاموس"""
        self.dynamic_data = json.dumps(data_dict)
    
    def __repr__(self):
        return f'<News {self.title}>'

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
