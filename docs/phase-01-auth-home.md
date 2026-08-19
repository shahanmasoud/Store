# Phase 01: Auth And Home

## Goal

فاز اول باید پروژه را قابل اجرا کند: بک‌اند FastAPI، فرانت‌اند React، صفحه لاگین، داشبورد اولیه و مسیر محافظت‌شده بعد از ورود.

## Backend Contract

Base path:

```text
/api/v1
```

Endpoints:

```text
POST /auth/login
GET /auth/me
```

Login input:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Expected login output:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "full_name": "مدیر سیستم"
  }
}
```

## Frontend Requirements

- رابط کاملا فارسی و RTL باشد.
- صفحه اول بدون توکن، لاگین باشد.
- بعد از لاگین، داشبورد عملیاتی نمایش داده شود.
- داشبورد کارت‌های مسیرهای اصلی را نشان دهد: فروش، کالاها، خرید، انبار، دفتر حساب، چک‌ها، گزارش‌ها.
- ماژول‌های بعدی در فاز اول فقط وضعیت آماده‌سازی/به‌زودی داشته باشند.

## Acceptance

- بک‌اند بدون خطای import بالا بیاید.
- لاگین موفق توکن بدهد.
- لاگین ناموفق پیام فارسی بدهد.
- `/auth/me` بدون توکن رد شود و با توکن کاربر را برگرداند.
- فرانت‌اند لاگین، خطا، loading، داشبورد و خروج را پوشش دهد.
