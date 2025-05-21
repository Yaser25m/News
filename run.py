#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
نقطة الدخول الرئيسية لنظام مراقبة الإعلام
هذا الملف يقوم بتشغيل تطبيق Flask
"""

import os
import sys
import importlib.util

# التأكد من تثبيت المكتبات المطلوبة
try:
    import dateutil
    import pytz
    print("تم التحقق من وجود المكتبات المطلوبة")
except ImportError as e:
    print(f"خطأ: {e}")
    print("جاري تثبيت المكتبات المطلوبة...")
    os.system("pip install python-dateutil pytz")
    print("تم تثبيت المكتبات المطلوبة")

# طباعة رسالة ترحيبية
print("=" * 50)
print("بدء تشغيل نظام مراقبة الإعلام")
print("الرجاء الانتظار...")
print("=" * 50)

# تشغيل التطبيق
if __name__ == '__main__':
    # استيراد التطبيق من app.py مباشرة
    spec = importlib.util.spec_from_file_location("app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    app = app_module.app

    # تم إزالة استيراد المجدول

    # تحديد إعدادات التشغيل حسب البيئة
    # إذا كان التطبيق يعمل على منصة Cloudflare Pages
    if 'CF_PAGES' in os.environ:
        # تشغيل التطبيق على منصة Cloudflare Pages
        app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    # إذا كان التطبيق يعمل على منصة Replit
    elif 'REPLIT_DB_URL' in os.environ:
        # تشغيل التطبيق على منصة Replit
        app.run(debug=False, host='0.0.0.0', port=8080)
    else:
        # تشغيل التطبيق محلياً
        app.run(debug=True, host='127.0.0.1', port=5000)
