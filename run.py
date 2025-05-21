#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
نقطة الدخول الرئيسية لنظام مراقبة الإعلام
هذا الملف يقوم بتشغيل تطبيق Flask
"""

import os
import sys
import importlib.util

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

    # تشغيل التطبيق
    app.run(debug=True, host='127.0.0.1', port=5000)
