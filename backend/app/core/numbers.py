import re
from typing import Any

_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_PLAIN_INTEGER_RE = re.compile(r"^[+-]?\d+$", re.ASCII)
_GROUPED_INTEGER_RE = re.compile(r"^[+-]?\d{1,3}(?P<separator>[,٬])\d{3}(?:(?P=separator)\d{3})*$", re.ASCII)
_PLAIN_DECIMAL_RE = re.compile(r"^[+-]?\d+(?:[.٫]\d+)?$", re.ASCII)
_GROUPED_DECIMAL_RE = re.compile(
    r"^[+-]?\d{1,3}(?P<separator>[,٬])\d{3}(?:(?P=separator)\d{3})*(?:[.٫]\d+)?$",
    re.ASCII,
)


def normalize_digits(value: str) -> str:
    """Convert Persian/Arabic digits to ASCII without changing punctuation."""
    return value.translate(_DIGIT_TRANSLATION)


def normalize_identifier(value: Any) -> Any:
    """Trim textual identifiers and normalize digits, preserving punctuation."""
    if not isinstance(value, str):
        return value
    return normalize_digits(value.strip())


def normalize_localized_integer(value: Any) -> Any:
    """Normalize an integer string with optional valid thousands grouping."""
    if not isinstance(value, str):
        return value
    normalized = normalize_digits(value.strip())
    if _PLAIN_INTEGER_RE.fullmatch(normalized):
        return normalized
    if _GROUPED_INTEGER_RE.fullmatch(normalized):
        return normalized.replace(",", "").replace("٬", "")
    raise ValueError("عدد را با رقم‌های معتبر و جداکنندهٔ سه‌رقمی درست وارد کنید.")


def normalize_localized_decimal(value: Any) -> Any:
    """Normalize decimal digits, thousands separators and Persian decimal mark."""
    if not isinstance(value, str):
        return value
    normalized = normalize_digits(value.strip())
    if not (_PLAIN_DECIMAL_RE.fullmatch(normalized) or _GROUPED_DECIMAL_RE.fullmatch(normalized)):
        raise ValueError("عدد اعشاری را با قالب معتبر وارد کنید.")
    return normalized.replace(",", "").replace("٬", "").replace("٫", ".")
