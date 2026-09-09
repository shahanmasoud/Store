from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.time import validate_jalali_date, validate_local_time
from app.core.numbers import normalize_identifier, normalize_localized_decimal, normalize_localized_integer
from app.schemas.catalog import ProductVariantRead
from app.schemas.ledger import PersonRead
from app.schemas.purchases import InventoryRead

PaymentMethod = Literal["cash", "card", "transfer", "credit", "cheque", "voucher"]
PaymentStatus = Literal["received", "pending"]
InvoiceStatus = Literal["active", "canceled"]


class SaleInvoiceItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal = Field(gt=0)
    unit_price_rial: int = Field(ge=0)
    discount_amount_rial: int = Field(default=0, ge=0)
    estimated_cost_rial: int | None = Field(default=None, ge=0)

    @field_validator("variant_id", "unit_price_rial", "discount_amount_rial", "estimated_cost_rial", mode="before")
    @classmethod
    def localized_integers(cls, value):
        return normalize_localized_integer(value)

    @field_validator("quantity", mode="before")
    @classmethod
    def localized_quantity(cls, value):
        return normalize_localized_decimal(value)


class SaleInvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_id: int
    quantity: Decimal
    unit_price_rial: int
    discount_amount_rial: int
    line_total_rial: int
    estimated_cost_rial: int | None
    estimated_profit_rial: int | None
    product_snapshot: str


class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount_rial: int = Field(gt=0)
    status: PaymentStatus | None = None
    reference_number: str | None = Field(default=None, max_length=120)
    jalali_date: str | None = None
    local_time: str | None = None
    due_jalali_date: str | None = None
    note: str | None = None

    @field_validator("amount_rial", mode="before")
    @classmethod
    def localized_amount(cls, value):
        return normalize_localized_integer(value)

    @field_validator("reference_number", mode="before")
    @classmethod
    def normalize_reference(cls, value):
        return normalize_identifier(value)

    @field_validator("jalali_date", "due_jalali_date")
    @classmethod
    def optional_jalali_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def optional_local_time_format(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_local_time(value)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    method: PaymentMethod
    amount_rial: int
    status: PaymentStatus
    reference_number: str | None
    jalali_date: str
    local_time: str
    timezone: str
    due_jalali_date: str | None
    note: str | None
    updated_at_utc: datetime | None


class PaymentDueDateUpdate(BaseModel):
    due_jalali_date: str | None
    reason: str = Field(min_length=1, max_length=2000)
    expected_updated_at: datetime

    @field_validator("due_jalali_date")
    @classmethod
    def due_date_format(cls, value: str | None) -> str | None:
        return validate_jalali_date(value) if value is not None else None

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("دلیل تغییر سررسید الزامی است.")
        return value


class PaymentDueAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    actor_user_id: int | None
    actor_username: str | None
    actor_full_name: str | None
    before_due_date: str | None
    after_due_date: str | None
    reason: str
    occurred_at_utc: datetime


class SaleInvoiceCreate(BaseModel):
    customer_id: int | None = Field(default=None, gt=0)
    customer_name: str | None = Field(default=None, max_length=160)
    jalali_date: str
    local_time: str
    discount_amount_rial: int = Field(default=0, ge=0)
    note: str | None = None
    items: list[SaleInvoiceItemCreate] = Field(min_length=1)
    payments: list[PaymentCreate] = Field(default_factory=list)

    @field_validator("customer_id", "discount_amount_rial", mode="before")
    @classmethod
    def localized_integers(cls, value):
        return normalize_localized_integer(value)

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)

    @model_validator(mode="after")
    def validate_total_is_not_negative(self) -> "SaleInvoiceCreate":
        subtotal = sum(
            int((item.quantity * item.unit_price_rial).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            - item.discount_amount_rial
            for item in self.items
        )
        if subtotal < 0:
            raise ValueError("جمع ردیف‌های فاکتور نمی‌تواند منفی باشد.")
        if subtotal - self.discount_amount_rial < 0:
            raise ValueError("تخفیف فاکتور نمی‌تواند از جمع ردیف‌ها بیشتر باشد.")
        return self


class SaleInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str | None
    customer_id: int | None
    customer_name: str | None
    subtotal_rial: int
    discount_amount_rial: int
    total_rial: int
    paid_total_rial: int
    due_total_rial: int
    status: InvoiceStatus
    is_active: bool
    jalali_date: str
    local_time: str
    timezone: str
    note: str | None
    items: list[SaleInvoiceItemRead]
    payments: list[PaymentRead]


class DailyJournalPaymentBreakdown(BaseModel):
    method: PaymentMethod
    received_rial: int = 0
    pending_rial: int = 0


class DailyJournalRead(BaseModel):
    jalali_date: str
    invoice_count: int
    sales_total_rial: int
    received_total_rial: int
    pending_total_rial: int
    estimated_profit_rial: int
    payments: list[DailyJournalPaymentBreakdown]


class SalesFormOptionsRead(BaseModel):
    variants: list[ProductVariantRead]
    inventory: list[InventoryRead]
    customers: list[PersonRead]
