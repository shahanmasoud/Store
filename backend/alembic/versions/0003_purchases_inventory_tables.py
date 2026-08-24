"""purchases inventory tables

Revision ID: 0003_purchases_inventory_tables
Revises: 0002_sales_mvp_tables
Create Date: 2026-08-24
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_purchases_inventory_tables"
down_revision: str | None = "0002_sales_mvp_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suppliers_id"), "suppliers", ["id"], unique=False)
    op.create_index(op.f("ix_suppliers_name"), "suppliers", ["name"], unique=False)

    op.create_table(
        "purchase_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=40), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("supplier_name", sa.String(length=160), nullable=True),
        sa.Column("subtotal_rial", sa.Integer(), nullable=False),
        sa.Column("discount_amount_rial", sa.Integer(), nullable=False),
        sa.Column("extra_cost_rial", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index(op.f("ix_purchase_invoices_id"), "purchase_invoices", ["id"], unique=False)
    op.create_index(op.f("ix_purchase_invoices_jalali_date"), "purchase_invoices", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_purchase_invoices_status"), "purchase_invoices", ["status"], unique=False)

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity_on_hand", sa.Numeric(12, 3), nullable=False),
        sa.Column("weighted_average_cost_rial", sa.Integer(), nullable=False),
        sa.Column("reorder_level", sa.Numeric(12, 3), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id"),
    )
    op.create_index(op.f("ix_inventory_items_id"), "inventory_items", ["id"], unique=False)
    op.create_index(op.f("ix_inventory_items_variant_id"), "inventory_items", ["variant_id"], unique=False)

    op.create_table(
        "purchase_invoice_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost_rial", sa.Integer(), nullable=False),
        sa.Column("extra_cost_rial", sa.Integer(), nullable=False),
        sa.Column("line_total_rial", sa.Integer(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["purchase_invoices.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_invoice_items_id"), "purchase_invoice_items", ["id"], unique=False)
    op.create_index(op.f("ix_purchase_invoice_items_invoice_id"), "purchase_invoice_items", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_purchase_invoice_items_variant_id"), "purchase_invoice_items", ["variant_id"], unique=False)

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("purchase_invoice_id", sa.Integer(), nullable=True),
        sa.Column("purchase_invoice_item_id", sa.Integer(), nullable=True),
        sa.Column("transaction_type", sa.String(length=30), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost_rial", sa.Integer(), nullable=True),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["purchase_invoice_id"], ["purchase_invoices.id"]),
        sa.ForeignKeyConstraint(["purchase_invoice_item_id"], ["purchase_invoice_items.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_transactions_id"), "inventory_transactions", ["id"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_jalali_date"), "inventory_transactions", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_transaction_type"), "inventory_transactions", ["transaction_type"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_variant_id"), "inventory_transactions", ["variant_id"], unique=False)

    op.create_table(
        "purchase_lots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("purchase_invoice_item_id", sa.Integer(), nullable=False),
        sa.Column("original_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost_rial", sa.Integer(), nullable=False),
        sa.Column("total_cost_rial", sa.Integer(), nullable=False),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["purchase_invoice_item_id"], ["purchase_invoice_items.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_lots_id"), "purchase_lots", ["id"], unique=False)
    op.create_index(op.f("ix_purchase_lots_jalali_date"), "purchase_lots", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_purchase_lots_status"), "purchase_lots", ["status"], unique=False)
    op.create_index(op.f("ix_purchase_lots_variant_id"), "purchase_lots", ["variant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_lots_variant_id"), table_name="purchase_lots")
    op.drop_index(op.f("ix_purchase_lots_status"), table_name="purchase_lots")
    op.drop_index(op.f("ix_purchase_lots_jalali_date"), table_name="purchase_lots")
    op.drop_index(op.f("ix_purchase_lots_id"), table_name="purchase_lots")
    op.drop_table("purchase_lots")
    op.drop_index(op.f("ix_inventory_transactions_variant_id"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_transaction_type"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_jalali_date"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_id"), table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    op.drop_index(op.f("ix_purchase_invoice_items_variant_id"), table_name="purchase_invoice_items")
    op.drop_index(op.f("ix_purchase_invoice_items_invoice_id"), table_name="purchase_invoice_items")
    op.drop_index(op.f("ix_purchase_invoice_items_id"), table_name="purchase_invoice_items")
    op.drop_table("purchase_invoice_items")
    op.drop_index(op.f("ix_inventory_items_variant_id"), table_name="inventory_items")
    op.drop_index(op.f("ix_inventory_items_id"), table_name="inventory_items")
    op.drop_table("inventory_items")
    op.drop_index(op.f("ix_purchase_invoices_status"), table_name="purchase_invoices")
    op.drop_index(op.f("ix_purchase_invoices_jalali_date"), table_name="purchase_invoices")
    op.drop_index(op.f("ix_purchase_invoices_id"), table_name="purchase_invoices")
    op.drop_table("purchase_invoices")
    op.drop_index(op.f("ix_suppliers_name"), table_name="suppliers")
    op.drop_index(op.f("ix_suppliers_id"), table_name="suppliers")
    op.drop_table("suppliers")
