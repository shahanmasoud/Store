# Store Automation

سیستم اتوماسیون فروشگاه حبوبات با بک‌اند Python/FastAPI، فرانت‌اند React/TypeScript و پایگاه داده SQLite.

## وضعیت فازها

1. اسکلت پروژه، هوم‌پیج و لاگین
2. هسته داده، زمان شمسی و مدل‌های پایه
3. فروش روزانه
4. خرید، انبار و قیمت تمام‌شده
5. دفتر حساب، چک و سررسیدها
6. گزارش‌ها و تحلیل مدیریتی
7. اتصال آنلاین و سفارش سایت
8. آماده‌سازی اجرای یکپارچه و تحویل

## اجرا

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.scripts.seed_admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
pnpm install
pnpm run dev
```

کاربر پیش‌فرض توسعه:

```text
username: admin
password: admin123
```

## تست

Backend:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend
```

Frontend build:

```powershell
cd frontend
pnpm run build
```

Health checks:

- `GET /health`
- `GET /ready`

Local smoke check after the backend is running:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.scripts.smoke_local
```

## معماری

- Backend: FastAPI, SQLAlchemy, Alembic, SQLite
- Frontend: React, TypeScript, Vite
- UI: فارسی، راست‌به‌چپ، ساده برای کاربر کم‌تجربه، با استاندارد `premium-frontend`
- زمان: ذخیره فنی UTC در کنار تاریخ و ساعت شمسی نمایشی
- داده مالی: حذف فیزیکی ممنوع؛ اصلاح، لغو یا برگشت ثبت می‌شود
