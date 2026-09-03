from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.time import validate_jalali_date


class DateRangeQuery(BaseModel):
    from_jalali: str
    to_jalali: str

    @field_validator("from_jalali", "to_jalali")
    @classmethod
    def jalali_date_format(cls, value: str) -> str:
        return validate_jalali_date(value)


class SalesSummaryRead(BaseModel):
    from_jalali: str
    to_jalali: str
    invoice_count: int
    registered_sales_rial: int
    received_rial: int
    pending_rial: int
    average_invoice_rial: int


class ProfitLossRead(BaseModel):
    from_jalali: str
    to_jalali: str
    sales_rial: int
    estimated_cost_rial: int
    gross_profit_rial: int
    gross_margin_percent: float


class InventoryRowRead(BaseModel):
    variant_id: int
    variant_name: str
    quantity_on_hand: Decimal
    weighted_average_cost_rial: int
    estimated_value_rial: int
    reorder_level: Decimal | None
    needs_reorder: bool


class InventoryReportRead(BaseModel):
    item_count: int
    total_value_rial: int
    low_stock_count: int
    items: list[InventoryRowRead]


class CashflowReportRead(BaseModel):
    jalali_date_to: str
    pending_sales_payments_rial: int
    unallocated_sales_due_rial: int
    total_sales_receivables_rial: int
    open_customer_receivables_rial: int
    open_supplier_payables_rial: int
    open_ledger_rial: int
    pending_received_cheques_rial: int
    pending_paid_cheques_rial: int
    net_expected_rial: int


class CustomerDebtRowRead(BaseModel):
    person_id: int
    person_name: str
    remaining_rial: int


class CustomerDebtReportRead(BaseModel):
    total_remaining_rial: int
    people: list[CustomerDebtRowRead]
