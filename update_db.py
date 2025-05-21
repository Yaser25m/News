import os
import sqlite3
import sys
import shutil
from datetime import datetime

def backup_database(db_path):
    """عمل نسخة احتياطية من قاعدة البيانات"""
    if not os.path.exists(db_path):
        return False

    # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجودًا
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # إنشاء اسم ملف النسخة الاحتياطية
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'relational_app_{timestamp}.db')

    # نسخ قاعدة البيانات
    try:
        shutil.copy2(db_path, backup_path)
        print(f"تم عمل نسخة احتياطية من قاعدة البيانات في: {backup_path}")
        return True
    except Exception as e:
        print(f"فشل عمل نسخة احتياطية: {str(e)}")
        return False

def recreate_news_source_table():
    """إعادة إنشاء جدول news_source مع الأعمدة الجديدة"""
    print("بدء إعادة إنشاء جدول news_source...")

    # التحقق من وجود قاعدة البيانات
    db_path = 'relational_app.db'
    if not os.path.exists(db_path):
        print(f"خطأ: قاعدة البيانات غير موجودة في المسار {db_path}")
        return False

    # عمل نسخة احتياطية أولاً
    if not backup_database(db_path):
        print("تحذير: فشل عمل نسخة احتياطية، هل تريد المتابعة؟ (y/n)")
        response = input().lower()
        if response != 'y':
            print("تم إلغاء العملية.")
            return False

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # استخراج البيانات الحالية
        cursor.execute("SELECT id, name, url, source_type, is_active, is_iraqi, created_at, updated_at FROM news_source")
        sources = cursor.fetchall()

        # إنشاء جدول مؤقت
        cursor.execute("""
        CREATE TABLE news_source_temp (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            source_type TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            is_iraqi BOOLEAN DEFAULT 0,
            can_fetch_news BOOLEAN DEFAULT 0,
            news_count INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)

        # نقل البيانات إلى الجدول المؤقت
        for source in sources:
            cursor.execute("""
            INSERT INTO news_source_temp (id, name, url, source_type, is_active, is_iraqi, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, source)

        # حذف الجدول القديم
        cursor.execute("DROP TABLE news_source")

        # إعادة تسمية الجدول المؤقت
        cursor.execute("ALTER TABLE news_source_temp RENAME TO news_source")

        # حفظ التغييرات
        conn.commit()
        print(f"تم إعادة إنشاء جدول news_source بنجاح مع {len(sources)} مصدر!")
        return True

    except Exception as e:
        print(f"حدث خطأ أثناء إعادة إنشاء الجدول: {str(e)}")
        conn.rollback()
        return False

    finally:
        # إغلاق الاتصال
        conn.close()

if __name__ == "__main__":
    recreate_news_source_table()
