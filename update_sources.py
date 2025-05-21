#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
سكريبت لتحديث مصادر الأخبار في قاعدة البيانات
"""

import sqlite3
import sys
import os

# قائمة المصادر المطلوبة
required_sources = [
    (4, "السومرية نيوز", "https://www.alsumaria.tv/iraq-news/48/%D9%85%D8%AD%D9%84%D9%8A%D8%A7%D8%AA"),
    (9, "قناة الرشيد", "https://www.alrasheedmedia.com/"),
    (15, "وكالة المعلومة", "https://www.almaalomah.me/"),
    (16, "وكالة نون الخبرية", "https://www.non14.net/"),
    (17, "وكالة أخبار العراق", "https://www.iraqakhbar.com/"),
    (23, "صحيفة المدى", "https://almadapaper.net/category/%d9%85%d8%ad%d9%84%d9%8a%d8%a7%d8%aa/"),
    (24, "صحيفة الزمان", "https://www.azzaman.com/"),
    (27, "صحيفة الدستور", "https://www.addustour.com/"),
    (30, "صحيفة الصباح الجديد", "https://www.newsabah.com/"),
    (31, "ناس نيوز", "https://www.nasnews.com/"),
    (32, "بغداد اليوم", "https://baghdadtoday.news/lastnews"),
    (36, "كتابات في الميزان", "https://kitabat.com/"),
    (40, "المسلة", "https://almasalah.com/"),
    (42, "موسوعة الرافدين", "https://www.alrafidain.news/"),
    (45, "شفق نيوز", "https://shafaq.com/ar/%D9%85%D8%AC%D8%AA%D9%80%D9%85%D8%B9"),
    (46, "السومرية نيوز", "https://www.alsumaria.tv/"),
    (47, "المربد", "https://www.al-mirbad.com/Latest"),
    (48, "بغداد اليوم", "https://baghdadtoday.news/"),
    (49, "وكالة اليوم", "https://today-agency.net/News/8/%D9%85%D8%AD%D9%84%D9%8A"),
    (50, "شبكة الساعة", "https://alssaa.com/posts/all"),
    (51, "الجبال", "https://aljeebal.com/posts"),
    (52, "قناة الاولى", "https://alawla.tv/local/"),
    (53, "ميل نيوز", "https://miliq.news/local/"),
    (54, "المسرى", "https://almasra.iq/category/%d8%a7%d9%84%d8%b9%d8%b1%d8%a7%d9%82/"),
    (56, "IQ News", "https://www.iqiraq.news/lastnews"),
    (57, "تايتل", "https://title.news/local/"),
    (58, "صحيفة المدى", "https://www.almadapaper.net/"),
    (59, "شبكة اخبار الناصرية", "https://nasiriyah.org/ar/post/category/allnews/"),
    (60, "عراق اوبزيرفر", "https://observeriraq.net/category/%d8%a7%d9%84%d8%b9%d8%b1%d8%a7%d9%82/")
]

def main():
    # التحقق من وجود قاعدة البيانات
    if not os.path.exists('relational_app.db'):
        print("خطأ: قاعدة البيانات غير موجودة")
        sys.exit(1)

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect('relational_app.db')
    cursor = conn.cursor()

    # الحصول على قائمة المصادر الحالية
    cursor.execute('SELECT id, name, url FROM news_source')
    existing_sources = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    # تحديث المصادر الموجودة وإضافة المصادر الجديدة
    updated_count = 0
    added_count = 0

    for source_id, name, url in required_sources:
        if source_id in existing_sources:
            # تحديث المصدر الموجود إذا كان الرابط مختلفًا
            if existing_sources[source_id][1] != url:
                cursor.execute('UPDATE news_source SET url = ? WHERE id = ?', (url, source_id))
                print(f"تم تحديث المصدر: {name} (ID: {source_id})")
                updated_count += 1
        else:
            # إضافة مصدر جديد
            cursor.execute('''
                INSERT INTO news_source (id, name, url, source_type, is_active, is_iraqi, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (source_id, name, url, 'website', 1, 1))
            print(f"تم إضافة المصدر: {name} (ID: {source_id})")
            added_count += 1

    # حفظ التغييرات
    conn.commit()
    conn.close()

    print(f"\nتم تحديث {updated_count} مصدر وإضافة {added_count} مصدر جديد")

if __name__ == '__main__':
    main()
