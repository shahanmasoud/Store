# فاز ۲۵ — bundle امن دیتابیس و تصاویر

## محدوده تحویل

این فاز هسته محلی بکاپ کامل را اضافه می‌کند و هیچ اتصال یا تغییری روی production ندارد. فرمان‌های قدیمی بکاپ SQLite برای سازگاری باقی مانده‌اند، اما مسیر عملیاتی جدید `bundle` است.

هر bundle در یک پوشه staging ساخته می‌شود و شامل snapshot سازگار SQLite، تمام فایل‌های `MEDIA_ROOT`، manifest نسخه‌دار با اندازه و SHA-256 و checksum اجباری خود manifest است. تا زمانی که verify کامل موفق نشود، نام نهایی منتشر نمی‌شود.

## ایمنی و هم‌زمانی

- بکاپ و upload/delete تصویر از یک advisory lock بین‌پردازه‌ای کنار `MEDIA_ROOT` استفاده می‌کنند.
- timeout بکاپ قابل تنظیم است؛ timeout تصویر به پاسخ 503 قابل retry تبدیل می‌شود.
- symlink در media پذیرفته نمی‌شود و مسیرهای مطلق، تکراری یا دارای `..` در manifest رد می‌شوند.
- verifier علاوه بر hash/size و `PRAGMA integrity_check`، وجود فایل تمام `products.image_filename`ها را بررسی می‌کند.
- restore فقط به دو مقصد ناموجود انجام می‌شود و overwrite production ندارد.
- retention فقط پوشه‌های نهایی با prefix استاندارد را حذف می‌کند و حداقل `keep-last` را حفظ می‌کند؛ فقط پس از ساخته‌شدن bundle تازه اجرا می‌شود.

## تست خودکار

```powershell
cd backend
python -m pytest tests\test_sqlite_backup.py tests\test_backup_bundle.py tests\test_storefront_media.py -q
```

نتیجه در زمان تحویل: `31 passed`. پوشش شامل round-trip دیتابیس و دو فایل رسانه، checksum مفقود/دستکاری‌شده، انتشار امن checksum قدیمی، خرابی DB و media، تصویر ارجاع‌شده مفقود، مسیرهای هم‌پوشان، lock contention، شکست میانی بدون انتشار، جلوگیری از overwrite restore و retention فقط روی bundle معتبر است. همچنین دیتابیس legacy که جدول `products` آن هنوز ستون `image_filename` ندارد، پیش از migration قابل bundle، verify و restore است و تعداد ارجاع تصویر صفر گزارش می‌شود.

## تست دستی کوتاه قبل از production

1. در یک محیط آزمایشی، `bundle` را با مسیرهای صریح DB و media اجرا کنید.
2. `verify-bundle` را روی خروجی اجرا و تعداد media/reference را ثبت کنید.
3. `restore-bundle` را به یک پوشه کاملاً تازه اجرا کنید.
4. برنامه آزمایشی را با DB و media بازیابی‌شده بالا بیاورید؛ کالاها، اشخاص، فاکتورها، چک‌ها، مانده‌ها و تصاویر فروشگاه را کنترل کنید.
5. در Chrome دسکتاپ و نمای موبایل، فهرست کالا و تصاویر را smoke-test کنید؛ نباید تصویر شکسته یا اسکرول افقی دیده شود.

## موارد خارج از این برش

- اجرای واقعی Scheduled Task و نخستین restore آزمایشی production نیازمند بازبینی و تأیید کاربر است.
- اعلان خودکار شکست و مقصد رمزنگاری‌شده off-host به انتخاب سرویس/credential نیاز دارد و فاز بعدی BAK-002 است.
