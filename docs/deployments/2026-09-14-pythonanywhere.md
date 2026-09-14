# گزارش استقرار PythonAnywhere — ۱۴ سپتامبر ۲۰۲۶

## نسخه و مقصد

- دامنه: `hobubat.pythonanywhere.com`
- commit مستقرشده: `221a702`
- commit قبلی: `c6aaeab`
- migration نهایی: `0019_sale_ledger_allocations (head)`

## حفاظت داده پیش از migration

- bundle کامل و verify‌شده: `store-bundle-20260914T200050.245946Z`
- محل نگهداری: `/home/Hobubat/store-backups/` خارج از checkout و Git
- محتوای media هنگام استقرار: صفر فایل و صفر ارجاع تصویر
- restore آزمایشی در مسیر جدا با موفقیت انجام شد.
- تمام migrationهای `0008` تا `0019` ابتدا روی restore اجرا شدند.
- dry-run reconciliation روی restore: `eligible_sales=0`، `exact=0`،
  `missing=0` و `conflict=0` با exit code صفر.

ابزار bundle در همین استقرار برای schema قدیمیِ قبل از ستون
`products.image_filename` سازگار شد؛ regression مربوطه در مجموعه ۲۴۸ تست بک‌اند
وجود دارد.

## نتیجه rollout

- نصب dependencyها موفق بود؛ `bcrypt 4.0.1`، `Pillow` و
  `python-multipart` نصب شدند.
- migration واقعی تا head موفق بود.
- Reload از Web panel با پیام `Reload successful` انجام شد.
- `/health` و `/ready` سالم بودند.
- صفحه اصلی و `/admin` پاسخ ۲۰۰ دادند.
- artifact فعال `index-BL6Zm-aT.js` بود.
- API کاتالوگ پاسخ ۲۰۰ و ۶۶ آیتم فعال برگرداند.
- `PRAGMA integrity_check` برابر `ok` بود.
- شمارش کنترل حفظ داده: یک کاربر، ۲۰ شخص، ۳۴ دسته، ۳۶ کالا و ۶۸ گونه.

## ورود بله

پس از Reload، webhook قدیمی به علت محدودیت ارتباط خروجی callback چند پاسخ ۵۰۰
ایجاد کرد. تنظیم production از ابتدا `BALE_POLLING_FALLBACK=True` بود؛ اسکریپت
رسمی `configure_bale_webhook` با proxy PythonAnywhere اجرا شد، webhook حذف و
polling برای `@HStoreBot` فعال شد. پس از Reload دوم، در پنجره پایش ۱۵ثانیه‌ای:

- خطای ۵۰۰ جدید: صفر
- درخواست webhook جدید: صفر
- `/ready`: سالم

## بکاپ دوره‌ای

ابزار `scheduled_backup`، retention و status مانیتورپذیر آماده‌اند، اما صفحه
Tasks حساب فعلی اعلام می‌کند Scheduled Tasks فقط برای حساب پولی فعال است.
بنابراین هیچ task روزانه‌ای ایجاد نشد. تا ارتقای حساب، بکاپ باید پیش از هر deploy
و به‌صورت دستی اجرا شود. پس از ارتقا، فرمان مستندشده در `docs/sqlite-backup.md`
فعال و نخستین اجرای آن کنترل شود.

## تست دستی مالک

در دسکتاپ و موبایل، ورود مدیر، کالاها، اشخاص، فروش، خرید، انبار، دفتر حساب، چک‌ها،
گزارش‌ها، فروشگاه عمومی، آپلود یک تصویر آزمایشی و ورود مشتری با بله بررسی شود.
برای جلوگیری از تغییر ناخواسته اطلاعات مالی، عملیات ثبت/ویرایش فقط با رکورد تستی
مشخص انجام شود.
