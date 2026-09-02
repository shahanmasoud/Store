from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.time import validate_jalali_date, validate_local_time

PurchaseStatus = Literal["active", "canceled"]


def money_from_quantity(quantity: Decimal, unit_cost_rial: int) -> int:
    return int((quantity * unit_cost_rial).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)


class SupplierRead(SupplierCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class PurchaseInvoiceItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal = Field(gt=0)
    unit_cost_rial: int = Field(ge=0)
    extra_cost_rial: int = Field(default=0, ge=0)


class PurchaseInvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_id: int
    quantity: Decimal
    unit_cost_rial: int
    extra_cost_rial: int
    line_total_rial: int


class PurchaseInvoiceCreate(BaseModel):
    supplier_id: int | None = None
    supplier_name: str | None = Field(default=None, max_length=160)
    jalali_date: str
    local_time: str
    discount_amount_rial: int = Field(default=0, ge=0)
    extra_cost_rial: int = Field(default=0, ge=0)
    paid_total_rial: int = Field(default=0, ge=0)
    note: str | None = None
    items: list[PurchaseInvoiceItemCreate] = Field(min_length=1)

    @field_validator("jalali_date")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)

    @field_validator("local_time")
    @classmethod
    def local_time_format(cls, value: str) -> str:
        return validate_local_time(value)

    @model_validator(mode="after")
    def validate_total(self) -> "PurchaseInvoiceCreate":
        subtotal = sum(money_from_quantity(item.quantity, item.unit_cost_rial) + item.extra_cost_rial for item in self.items)
        if subtotal + self.extra_cost_rial - self.discount_amount_rial < 0:
            raise ValueError("جمع فاکتور خرید نمی‌تواند منفی باشد.")
        return self


class PurchaseInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str | None
    supplier_id: int | None
    supplier_name: str | None
    subtotal_rial: int
    discount_amount_rial: int
    extra_cost_rial: int
    total_rial: int
    paid_total_rial: int
    due_total_rial: int
    status: PurchaseStatus
    is_active: bool
    jalali_date: str
    local_time: str
    timezone: str
    note: str | None
    items: list[PurchaseInvoiceItemRead]


class InventoryRead(BaseModel):
    id: int
    variant_id: int
    variant_name: str
    quantity_on_hand: Decimal
    weighted_average_cost_rial: int
    reorder_level: Decimal | None


class InventoryUpdate(BaseModel):
    reorder_level: Decimal | None = Field(ge=0)


class InventoryTransactionRead(BaseModel):
    id: int
    variant_id: int
    variant_name: str
    purchase_invoice_id: int | None
    purchase_invoice_item_id: int | None
    transaction_type: str
    quantity_delta: Decimal
    balance_after: Decimal
    unit_cost_rial: int | None
    jalali_date: str
    local_time: str
    note: str | None
