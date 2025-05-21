#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
سكريبت لتصحيح أسماء المصادر وروابطها في قاعدة البيانات
"""

import sqlite3
import sys
import os

# قائمة التصحيحات
corrections = [
    (4, "السومرية نيوز", "https://www.alsumaria.tv/iraq-news/48/%D9%85%D8%AD%D9%84%D9%8A%D8%A7%D8%AA"),
    (9, "قناة الرشيد", "https://www.alrasheedmedia.com/"),
    (15, "وكالة المعلومة", "https://www.almaalomah.me/"),
    (16, "وكالة نون الخبرية", "https://www.non14.net/"),
    (23, "صحيفة المدى", "https://almadapaper.net/category/%d9%85%d8%ad%d9%84%d9%8a%d8%a7%d8%aa/"),
    (24, "صحيفة الزمان", "https://www.azzaman.com/"),
    (27, "صحيفة الدستور", "https://www.addustour.com/"),
    (30, "صحيفة الصباح الجديد", "https://www.newsabah.com/"),
]

def main():
    # التحقق من وجود قاعدة البيانات
    if not os.path.exists('relational_app.db'):
        print("خطأ: قاعدة البيانات غير موجودة")
        sys.exit(1)

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect('relational_app.db')
    cursor = conn.cursor()

    # تصحيح أسماء المصادر وروابطها
    for source_id, name, url in corrections:
        cursor.execute('UPDATE news_source SET name = ?, url = ? WHERE id = ?', (name, url, source_id))
        print(f"تم تصحيح المصدر: {name} (ID: {source_id})")

    # حذف المصادر المكررة
    cursor.execute('''
        DELETE FROM news_source
        WHERE id IN (
            SELECT id FROM news_source
            WHERE name IN (
                SELECT name FROM news_source
                GROUP BY name
                HAVING COUNT(*) > 1
            )
            AND id NOT IN (
                SELECT MIN(id) FROM news_source
                GROUP BY name
                HAVING COUNT(*) > 1
            )
        )
    ''')
    deleted_count = cursor.rowcount
    print(f"تم حذف {deleted_count} مصدر مكرر")

    # حفظ التغييرات
    conn.commit()
    conn.close()

    print("\nتم تصحيح المصادر بنجاح")

if __name__ == '__main__':
    main()
