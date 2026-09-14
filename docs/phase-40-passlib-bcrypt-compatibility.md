# فاز ۴۰ — سازگاری Passlib و bcrypt

## محدوده

رفع هشدار metadata هنگام hash/verify رمز، بدون تغییر الگوریتم bcrypt، بدون rehash کاربران و بدون دست‌زدن به دیتابیس یا محیط production.

## علت و تصمیم

- محیط توسعه پیش از اصلاح شامل `passlib 1.7.4` و `bcrypt 4.3.0` بود.
- Passlib 1.7.4 برای تشخیص نسخه به `bcrypt.__about__.__version__` مراجعه می‌کند؛ این metadata از bcrypt 4.1 حذف شده و در نتیجه traceback هشدارگونه روی stderr ثبت می‌شود، هرچند عملیات hash و verify ادامه پیدا می‌کند.
- dependency به `bcrypt>=4.0.0,<4.1.0` محدود شد. این تغییر backend رمزنگاری را در خانواده bcrypt نگه می‌دارد و فرمت `$2b$`، cost و هش‌های ذخیره‌شده را تغییر نمی‌دهد.
- همان محدودیت در `pyproject.toml`، `requirements.txt` و `constraints.txt` ثبت شد تا نصب توسعه و دستور استقرار PythonAnywhere نتیجه یکسانی داشته باشند.

## ایمنی داده و استقرار

- migration، تغییر schema، خواندن یا نوشتن دیتابیس واقعی و rehash انجام نمی‌شود.
- در استقرار بعدی، دستور موجود `pip install -r backend/requirements.txt` نسخه ناسازگار را به شاخه 4.0.x برمی‌گرداند؛ سپس Reload لازم است. این فاز خودکار deploy نشده است.
- rollback وابستگی فقط بازگرداندن constraint قبلی و نصب دوباره requirements است؛ هش‌های کاربران در هر دو حالت ثابت می‌مانند.

## معیار پذیرش و تست دستی

1. در یک virtualenv تمیز، requirements نصب شود و نسخه bcrypt کمتر از 4.1 باشد.
2. hash و verify بدون پیام `error reading bcrypt version` اجرا شوند.
3. یک هش `$2b$` از قبل ذخیره‌شده با رمز درست قبول و با رمز نادرست رد شود.
4. ورود مدیر، تغییر رمز و ورود زیرمدیر با سطح دسترسی همچنان موفق باشند.

این تغییر UI ندارد؛ QA جداگانه دسکتاپ/موبایل لازم نیست و پوشش مرورگری ورود موجود معتبر باقی می‌ماند.

## نتیجه آزمون خودکار

- `pip install --dry-run -r requirements.txt`: انتخاب `bcrypt 4.0.1` به‌جای نسخه نصب‌شده 4.3.0.
- نصب کامل `requirements-dev.txt` در virtualenv جدا با Python 3.13: موفق؛ `passlib 1.7.4` و `bcrypt 4.0.1`.
- `pytest tests/test_auth.py tests/test_user_admin_permissions.py -q`: تعداد `26 passed`.
- هشدار `error reading bcrypt version` در محیط تمیز دیده نشد. دو deprecation warning مستقل از bcrypt و متعلق به TestClient/AnyIO باقی ماندند.
