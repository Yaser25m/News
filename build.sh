#!/bin/bash
# هذا الملف يحتوي على تعليمات البناء لـ Cloudflare Pages

# تثبيت المتطلبات
pip install -r requirements.txt

# إنشاء المجلدات اللازمة
mkdir -p dist

# نسخ الملفات الضرورية إلى مجلد dist
cp -r app dist/
cp -r backups dist/
cp app.py dist/
cp config.py dist/
cp run.py dist/
cp .env dist/
cp requirements.txt dist/
cp relational_app.db dist/
cp relational_app.db.backup dist/
cp 404.html dist/

# إنشاء ملف _redirects في مجلد dist
echo "/* /index.html 200" > dist/_redirects

# طباعة رسالة نجاح
echo "تم بناء المشروع بنجاح!"
