# Store Automation

سیستم اتوماسیون مغازه حبوبات‌فروشی با بک‌اند Python/FastAPI، فرانت‌اند React و پایگاه داده SQLite.

## مسیر اجرا

پروژه بر اساس مستندات Word موجود در ریشه ریپو پیش می‌رود و فازها به ترتیب زیر ساخته می‌شوند:

1. اسکلت پروژه، هوم‌پیج و لاگین
2. هسته داده، زمان شمسی و مدل‌های پایه
3. MVP فروش روزانه
4. خرید، انبار و قیمت تمام‌شده
5. دفتر حساب، چک و سررسیدها
6. گزارش‌ها و تحلیل مدیریتی
7. آماده‌سازی اتصال آنلاین و سایت فروشگاهی

## معماری

- Backend: FastAPI, SQLAlchemy, SQLite
- Frontend: React, TypeScript, Vite
- UI: فارسی، راست‌به‌چپ، ساده برای کاربر کم‌تجربه، با استاندارد premium-frontend
- زمان: ذخیره فنی UTC در کنار تاریخ و ساعت شمسی نمایشی
- داده مالی: حذف فیزیکی ممنوع؛ اصلاح، لغو یا برگشت ثبت می‌شود

## Branching

- `main`: نسخه پایدار و تاییدشده
- `phase-01-auth-home`: شاخه کاری فاز اول

هر فاز بعد از پیاده‌سازی، review، تست و تایید معماری به `main` منتقل می‌شود.

## اجرای فاز اول

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m app.scripts.seed_admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
pnpm install
pnpm run dev
```

کاربر پیش‌فرض فاز اول:

```text
username: admin
password: admin123
```
