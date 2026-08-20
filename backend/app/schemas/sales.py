from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.time import validate_jalali_date, validate_local_time

PaymentMethod = Literal["cash", "card", "transfer", "credit", "cheque", "voucher"]
PaymentStatus = Literal["received", "pending"]
InvoiceStatus = Literal["active", "canceled"]


class SaleInvoiceItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal = Field(gt=0)
    unit_price_rial: int = Field(ge=0)
    discount_amount_rial: int = Field(default=0, ge=0)
    estimated_cost_rial: int | None = Field(default=None, ge=0)


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


class SaleInvoiceCreate(BaseModel):
    customer_name: str | None = Field(default=None, max_length=160)
    jalali_date: str
    local_time: str
    discount_amount_rial: int = Field(default=0, ge=0)
    note: str | None = None
    items: list[SaleInvoiceItemCreate] = Field(min_length=1)
    payments: list[PaymentCreate] = Field(default_factory=list)

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
            raise ValueError("Invoice subtotal cannot be negative.")
        if subtotal - self.discount_amount_rial < 0:
            raise ValueError("Invoice total cannot be negative.")
        return self


class SaleInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str | None
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
    payments: list[DailyJournalPaymentBreakdown]
