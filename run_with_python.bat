@echo off
echo ===== بدء تشغيل نظام مراقبة الإعلام =====
echo.

REM التأكد من وجود Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo خطأ: لم يتم العثور على Python. يرجى التأكد من تثبيت Python وإضافته إلى متغير PATH.
    goto :error
)

REM التأكد من وجود ملف run.py
if not exist run.py (
    echo خطأ: ملف run.py غير موجود في المجلد الحالي.
    goto :error
)

echo تشغيل التطبيق...
echo.

REM تشغيل التطبيق
python run.py

echo.
echo ===== انتهى التشغيل =====

:error
echo.
echo اضغط أي مفتاح للخروج...
pause >nul
