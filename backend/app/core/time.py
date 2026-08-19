from datetime import datetime, timezone
import re

TEHRAN_TIMEZONE = "Asia/Tehran"
JALALI_DATE_RE = re.compile(r"^1[34]\d{2}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])$")
LOCAL_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_jalali_date(value: str) -> str:
    if not JALALI_DATE_RE.match(value):
        raise ValueError("تاریخ شمسی باید با قالب 1403/01/01 وارد شود.")
    return value


def validate_local_time(value: str) -> str:
    if not LOCAL_TIME_RE.match(value):
        raise ValueError("ساعت باید با قالب 09:30 وارد شود.")
    return value
