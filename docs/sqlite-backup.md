# پشتیبان‌گیری امن از SQLite

این ابزار با API داخلی backup در SQLite یک snapshot سازگار می‌سازد؛ بنابراین برخلاف کپی مستقیم فایل دیتابیس، هنگام فعال بودن برنامه نیز ساختار فایل ناقص نمی‌شود. هر نسخه با `PRAGMA integrity_check` بررسی و فایل SHA-256 جداگانه برای آن ساخته می‌شود.

اطلاعات مالی یا فایل دیتابیس را در Git و GitHub قرار ندهید. فایل‌های `*.db`، `*.sqlite` و `*.sqlite3` در `.gitignore` هستند، اما محل پشتیبان نیز باید کاملاً بیرون از پوشه پروژه باشد.

فرمان قدیمی `backup` فقط SQLite را پوشش می‌دهد. برای داده عملیاتی از فرمان `bundle` استفاده کنید؛ این فرمان دیتابیس و کل `MEDIA_ROOT` را زیر یک قفل مشترک در staging می‌سازد، همه فایل‌ها و manifest را بررسی می‌کند و فقط سپس پوشه نهایی را اتمیک منتشر می‌کند.

## PythonAnywhere

متغیرهای خصوصی را بارگذاری و سپس از مسیر پیش‌فرض امن `~/store-backups` استفاده کنید:

```bash
cd ~/Store/backend
set -a
source ~/.store.env
set +a
~/.virtualenvs/store/bin/python -m app.scripts.sqlite_backup bundle --keep-days 30 --keep-last 7
```

دستور بالا مسیر دیتابیس و رسانه را از `DATABASE_URL` و `MEDIA_ROOT` می‌خواند. هر bundle شامل `store.db`، پوشه `media`، `manifest.json` و checksum اجباری manifest است. `--keep-days 30 --keep-last 7` نسخه‌های قدیمی را فقط پس از موفقیت نسخه تازه حذف می‌کند و همیشه هفت نسخه جدید را نگه می‌دارد.

```bash
bash -lc 'set -a; source ~/.store.env; set +a; cd ~/Store/backend && ~/.virtualenvs/store/bin/python -m app.scripts.sqlite_backup bundle --keep-days 30 --keep-last 7 >> ~/store-backups/scheduled.log 2>&1'
```

همین فرمان یک‌خطی برای PythonAnywhere Scheduled Tasks مناسب است. task باید روزانه اجرا شود؛ خروجی موفق با exit code صفر و عبارت `Backup bundle created and verified` پایان می‌یابد. خطا exit code غیرصفر دارد. فایل log را دوره‌ای rotate کنید و هیچ secretی در فرمان یا log ننویسید.

قفل مشترک مانع هم‌زمانی دو بکاپ و تغییر تصویر هنگام snapshot می‌شود؛ در زمان بکاپ، upload/delete تصویر ممکن است موقتاً پاسخ 503 بگیرد و قابل retry است. علاوه بر task روزانه، درست پیش از `git pull` یا migration یک bundle دستی بگیرید. پوشه و فایل‌ها در POSIX به‌ترتیب با permissionهای `700` و `600` محدود می‌شوند.

## اجرای محلی ویندوز

مقصد را بیرون worktree انتخاب کنید:

```powershell
cd C:\path\to\Store\backend
 .\.venv\Scripts\python.exe -m app.scripts.sqlite_backup bundle `
  --source .\store.db `
  --media-root .\media `
  --destination "$env:USERPROFILE\StoreBackups"
```

نسخه دوم بکاپ باید به‌صورت رمزنگاری‌شده روی دستگاه یا فضای ذخیره‌سازی دیگری نگهداری شود. کلید رمزنگاری نباید در مخزن یا کنار بکاپ ذخیره شود.

## بررسی و بازیابی آزمایشی

بررسی یک نسخه هیچ داده‌ای را تغییر نمی‌دهد:

```bash
python -m app.scripts.sqlite_backup verify-bundle ~/store-backups/store-bundle-TIMESTAMP
```

ابتدا همیشه در یک مسیر تازه بازیابی آزمایشی انجام دهید:

```bash
python -m app.scripts.sqlite_backup restore-bundle \
  ~/store-backups/store-bundle-TIMESTAMP \
  ~/store-restore-test/store.db \
  ~/store-restore-test/media
```

هر دو مقصد restore باید تازه و ناموجود باشند؛ ابزار هرگز داده موجود را جایگزین نمی‌کند. پس از restore، integrity دیتابیس و وجود تمام تصاویر ارجاع‌شده دوباره بررسی می‌شود. جایگزینی production بخشی از این ابزار نیست: ابتدا وب‌اپ را متوقف کنید، از وضعیت فعلی bundle تازه بگیرید و فقط با runbook جدا و تأیید انسانی جابه‌جایی را انجام دهید.

## کنترل دوره‌ای

- روزانه: موفقیت فرمان bundle، exit code، manifest و checksum را بررسی کنید.
- ماهانه: یک restore آزمایشی در مسیر جدا انجام دهید و برنامه را با کپی آزمایشی بالا بیاورید.
- پیش از هر migration: بکاپ مستقل بگیرید و نام آن را در گزارش استقرار ثبت کنید.
- verifier وجود فایل متناظر هر `products.image_filename` را کنترل می‌کند؛ smoke test فروشگاه پس از restore همچنان الزامی است.
- اعلان خودکار شکست و نسخه رمزنگاری‌شده off-host هنوز پیاده نشده‌اند؛ تا آن زمان log روزانه دستی بررسی و یک کپی رمزنگاری‌شده روی دستگاه دیگری نگهداری شود.
- فایل‌های بکاپ و لاگ‌ها نباید حاوی `SECRET_KEY`، توکن بله یا محتوای `~/.store.env` باشند.
