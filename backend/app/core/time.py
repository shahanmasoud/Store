from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TEHRAN_TIMEZONE = "Asia/Tehran"
JALALI_DATE_RE = re.compile(r"^1[34]\d{2}/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])$")
LOCAL_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gregorian_to_jalali(year: int, month: int, day: int) -> tuple[int, int, int]:
    """Convert a Gregorian date to Jalali without a platform-specific dependency."""
    gregorian_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy = year + 1 if month > 2 else year
    days = (
        355666
        + (365 * year)
        + ((gy + 3) // 4)
        - ((gy + 99) // 100)
        + ((gy + 399) // 400)
        + day
        + gregorian_days[month - 1]
    )
    jalali_year = -1595 + (33 * (days // 12053))
    days %= 12053
    jalali_year += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jalali_year += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jalali_month = 1 + (days // 31)
        jalali_day = 1 + (days % 31)
    else:
        jalali_month = 7 + ((days - 186) // 30)
        jalali_day = 1 + ((days - 186) % 30)
    return jalali_year, jalali_month, jalali_day


def current_jalali_date(now: datetime | None = None) -> str:
    """Return the current Tehran calendar date as a stable API-friendly string."""
    moment = now or utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    try:
        tehran_zone = ZoneInfo(TEHRAN_TIMEZONE)
    except ZoneInfoNotFoundError:
        # Iran has used a fixed UTC+03:30 offset since abolishing DST in 2022.
        # This keeps local development deterministic on Windows images without tzdata.
        tehran_zone = timezone(timedelta(hours=3, minutes=30), name=TEHRAN_TIMEZONE)
    tehran_now = moment.astimezone(tehran_zone)
    year, month, day = gregorian_to_jalali(tehran_now.year, tehran_now.month, tehran_now.day)
    return f"{year:04d}/{month:02d}/{day:02d}"


def validate_jalali_date(value: str) -> str:
    if not JALALI_DATE_RE.match(value):
        raise ValueError("تاریخ شمسی باید با قالب 1403/01/01 وارد شود.")
    return value


def validate_local_time(value: str) -> str:
    if not LOCAL_TIME_RE.match(value):
        raise ValueError("ساعت باید با قالب 09:30 وارد شود.")
    return value
