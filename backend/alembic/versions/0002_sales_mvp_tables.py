"""sales mvp tables

Revision ID: 0002_sales_mvp_tables
Revises: 0001_initial_core_tables
Create Date: 2026-08-20
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_sales_mvp_tables"
down_revision: str | None = "0001_initial_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sale_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=40), nullable=True),
        sa.Column("customer_name", sa.String(length=160), nullable=True),
        sa.Column("subtotal_rial", sa.Integer(), nullable=False),
        sa.Column("discount_amount_rial", sa.Integer(), nullable=False),
        sa.Column("total_rial", sa.Integer(), nullable=False),
        sa.Column("paid_total_rial", sa.Integer(), nullable=False),
        sa.Column("due_total_rial", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=40), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index(op.f("ix_sale_invoices_id"), "sale_invoices", ["id"], unique=False)
    op.create_index(op.f("ix_sale_invoices_jalali_date"), "sale_invoices", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_sale_invoices_status"), "sale_invoices", ["status"], unique=False)

    op.create_table(
        "sale_invoice_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price_rial", sa.Integer(), nullable=False),
        sa.Column("discount_amount_rial", sa.Integer(), nullable=False),
        sa.Column("line_total_rial", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_rial", sa.Integer(), nullable=True),
        sa.Column("estimated_profit_rial", sa.Integer(), nullable=True),
        sa.Column("product_snapshot", sa.String(length=180), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["sale_invoices.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sale_invoice_items_id"), "sale_invoice_items", ["id"], unique=False)
    op.create_index(op.f("ix_sale_invoice_items_invoice_id"), "sale_invoice_items", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_sale_invoice_items_variant_id"), "sale_invoice_items", ["variant_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount_rial", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reference_number", sa.String(length=120), nullable=True),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=40), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_jalali_date", sa.String(length=10), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["sale_invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_due_jalali_date"), "payments", ["due_jalali_date"], unique=False)
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_invoice_id"), "payments", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_payments_jalali_date"), "payments", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_payments_method"), "payments", ["method"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_method"), table_name="payments")
    op.drop_index(op.f("ix_payments_jalali_date"), table_name="payments")
    op.drop_index(op.f("ix_payments_invoice_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_due_jalali_date"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_sale_invoice_items_variant_id"), table_name="sale_invoice_items")
    op.drop_index(op.f("ix_sale_invoice_items_invoice_id"), table_name="sale_invoice_items")
    op.drop_index(op.f("ix_sale_invoice_items_id"), table_name="sale_invoice_items")
    op.drop_table("sale_invoice_items")
    op.drop_index(op.f("ix_sale_invoices_status"), table_name="sale_invoices")
    op.drop_index(op.f("ix_sale_invoices_jalali_date"), table_name="sale_invoices")
    op.drop_index(op.f("ix_sale_invoices_id"), table_name="sale_invoices")
    op.drop_table("sale_invoices")
