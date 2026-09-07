from decimal import Decimal

import pytest

from app.core.numbers import (
    normalize_digits,
    normalize_identifier,
    normalize_localized_decimal,
    normalize_localized_integer,
)
from app.core.time import validate_jalali_date, validate_local_time


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("۱۲۳۴۵۶", "123456"),
        ("١٢٣٤٥٦", "123456"),
        ("۱۲٣ABC", "123ABC"),
    ],
)
def test_normalize_digits(value: str, expected: str) -> None:
    assert normalize_digits(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("۱۲۳۴", "1234"),
        ("١٬٢٣٤٬٥٦٧", "1234567"),
        ("1,234,567", "1234567"),
        ("-۱۲٬۳۴۵", "-12345"),
    ],
)
def test_normalize_localized_integer(value: str, expected: str) -> None:
    assert normalize_localized_integer(value) == expected


@pytest.mark.parametrize("value", ["1,23", "۱٬۲۳", "1,234٬567", "1.2", "--12", "12x"])
def test_normalize_localized_integer_rejects_malformed(value: str) -> None:
    with pytest.raises(ValueError, match="جداکننده"):
        normalize_localized_integer(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("۲٫۵", "2.5"),
        ("١٢.٧٥", "12.75"),
        ("۱٬۲۳۴٫۵۰", "1234.50"),
        ("1,234.50", "1234.50"),
    ],
)
def test_normalize_localized_decimal(value: str, expected: str) -> None:
    assert normalize_localized_decimal(value) == expected
    assert Decimal(expected) == Decimal(normalize_localized_decimal(value))


@pytest.mark.parametrize("value", ["۱٫۲٫۳", "1,23.4", "1٬234,567", "12x"])
def test_normalize_localized_decimal_rejects_malformed(value: str) -> None:
    with pytest.raises(ValueError, match="قالب معتبر"):
        normalize_localized_decimal(value)


def test_identifier_preserves_punctuation_and_normalizes_only_digits_and_edges() -> None:
    assert normalize_identifier("  +۹۸ (٩١٢)-۳۴۵  ") == "+98 (912)-345"


def test_date_and_time_are_stored_in_ascii_canonical_form() -> None:
    assert validate_jalali_date("۱۴۰۵/۰۶/۰۷") == "1405/06/07"
    assert validate_local_time("۰۹:۳۰") == "09:30"
