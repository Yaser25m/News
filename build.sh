#!/bin/bash
# هذا الملف يحتوي على تعليمات البناء لـ Cloudflare Pages

# طباعة معلومات النظام
echo "===== معلومات النظام ====="
python --version
pip --version
echo "=========================="

# تثبيت المتطلبات
echo "تثبيت المتطلبات..."
pip install -r requirements.txt

# إنشاء المجلدات اللازمة
echo "إنشاء المجلدات اللازمة..."
mkdir -p dist

# نسخ الملفات الضرورية إلى مجلد dist
echo "نسخ الملفات الضرورية..."
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
cp index.html dist/

# إنشاء ملف _redirects في مجلد dist
echo "إنشاء ملف _redirects..."
echo "/*    /index.html   200" > dist/_redirects

# إنشاء ملف _headers في مجلد dist
echo "إنشاء ملف _headers..."
echo "/*" > dist/_headers
echo "  Content-Type: text/html; charset=UTF-8" >> dist/_headers

# طباعة محتويات مجلد dist
echo "محتويات مجلد dist:"
ls -la dist/

# طباعة رسالة نجاح
echo "تم بناء المشروع بنجاح!"
