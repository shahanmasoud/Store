# استقرار Store روی PythonAnywhere

این پروژه به‌صورت یک برنامه تک‌دامنه منتشر می‌شود: FastAPI هم API را اجرا می‌کند و هم خروجی production رابط React را از `backend/app/frontend` سرو می‌کند. بنابراین درخواست‌های production به `/api/v1` هم‌دامنه‌اند و به CORS جداگانه نیاز ندارند.

## پیش‌نیاز حساب

- System image حساب باید Python 3.11 یا جدیدتر داشته باشد؛ روی image جدید `innit` نسخه‌های 3.11 تا 3.13 موجودند.
- استقرار FastAPI از سازوکار ASGI آزمایشی PythonAnywhere و ابزار `pa` استفاده می‌کند.
- دامنه رایگان معمولاً `USERNAME.pythonanywhere.com` است؛ در حساب EU از `USERNAME.eu.pythonanywhere.com` استفاده کنید.

## آماده‌سازی در Bash console

مقادیر نمونه با حروف بزرگ را جایگزین کنید. رمزها را در چت، Git یا خروجی عمومی قرار ندهید.

```bash
cd ~
git clone https://github.com/shahanmasoud/Store.git
cd Store
python3.13 -m venv ~/.virtualenvs/store
~/.virtualenvs/store/bin/pip install -r backend/requirements.txt
mkdir -p ~/store-data
```

یک secret تصادفی و رمز مدیر قوی بسازید و متغیرهای محیطی را فقط در فرمان‌های خصوصی حساب تنظیم کنید:

```bash
cat > ~/.store.env <<'EOF'
DATABASE_URL=sqlite:////home/YOUR_USERNAME/store-data/store.db
SECRET_KEY=YOUR_RANDOM_SECRET
DEFAULT_ADMIN_USERNAME=YOUR_ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD=YOUR_STRONG_ADMIN_PASSWORD
EOF
chmod 600 ~/.store.env
set -a
source ~/.store.env
set +a
cd ~/Store/backend
~/.virtualenvs/store/bin/alembic upgrade head
~/.virtualenvs/store/bin/python -m app.scripts.seed_admin
```

## ساخت وب‌اپ ASGI

ابتدا در Account → API token یک token بسازید. سپس در Bash console:

```bash
~/.virtualenvs/store/bin/pip install --upgrade pythonanywhere
pa website create \
  --domain YOUR_USERNAME.pythonanywhere.com \
  --command '/bin/bash /home/YOUR_USERNAME/Store/deploy/pythonanywhere_start.sh'
```

پس از ایجاد یا هر به‌روزرسانی:

```bash
pa website reload --domain YOUR_USERNAME.pythonanywhere.com
```

## کنترل سلامت

```text
https://YOUR_USERNAME.pythonanywhere.com/health
https://YOUR_USERNAME.pythonanywhere.com/ready
https://YOUR_USERNAME.pythonanywhere.com/
https://YOUR_USERNAME.pythonanywhere.com/admin
```

## به‌روزرسانی‌های بعدی

خروجی React لازم برای PythonAnywhere در مخزن قرار دارد؛ Node روی سرور لازم نیست.

```bash
cd ~/Store
git pull --ff-only origin main
set -a
source ~/.store.env
set +a
cd backend
~/.virtualenvs/store/bin/alembic upgrade head
pa website reload --domain <USERNAME>.pythonanywhere.com
```

پیش از هر به‌روزرسانی از `~/store-data/store.db` نسخه پشتیبان بگیرید.
