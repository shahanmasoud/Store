"""online integration tables

Revision ID: 0005_online_integration_tables
Revises: 0004_ledger_cheques_dues_tables
Create Date: 2026-08-24
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_online_integration_tables"
down_revision: str | None = "0004_ledger_cheques_dues_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "online_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_online_channels_id"), "online_channels", ["id"], unique=False)
    op.create_index(op.f("ix_online_channels_name"), "online_channels", ["name"], unique=False)
    op.create_index(op.f("ix_online_channels_token_hash"), "online_channels", ["token_hash"], unique=False)

    op.create_table(
        "online_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("external_order_id", sa.String(length=120), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=True),
        sa.Column("customer_phone", sa.String(length=40), nullable=True),
        sa.Column("subtotal_rial", sa.Integer(), nullable=False),
        sa.Column("discount_amount_rial", sa.Integer(), nullable=False),
        sa.Column("total_rial", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=40), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["online_channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_online_orders_channel_id"), "online_orders", ["channel_id"], unique=False)
    op.create_index(op.f("ix_online_orders_external_order_id"), "online_orders", ["external_order_id"], unique=False)
    op.create_index(op.f("ix_online_orders_id"), "online_orders", ["id"], unique=False)
    op.create_index(op.f("ix_online_orders_jalali_date"), "online_orders", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_online_orders_status"), "online_orders", ["status"], unique=False)

    op.create_table(
        "online_price_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("price_rial", sa.Integer(), nullable=False),
        sa.Column("min_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("starts_jalali_date", sa.String(length=10), nullable=True),
        sa.Column("ends_jalali_date", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["online_channels.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_online_price_rules_channel_id"), "online_price_rules", ["channel_id"], unique=False)
    op.create_index(op.f("ix_online_price_rules_ends_jalali_date"), "online_price_rules", ["ends_jalali_date"], unique=False)
    op.create_index(op.f("ix_online_price_rules_id"), "online_price_rules", ["id"], unique=False)
    op.create_index(op.f("ix_online_price_rules_starts_jalali_date"), "online_price_rules", ["starts_jalali_date"], unique=False)
    op.create_index(op.f("ix_online_price_rules_variant_id"), "online_price_rules", ["variant_id"], unique=False)

    op.create_table(
        "online_order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price_rial", sa.Integer(), nullable=False),
        sa.Column("line_total_rial", sa.Integer(), nullable=False),
        sa.Column("product_snapshot", sa.String(length=180), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["online_orders.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_online_order_items_id"), "online_order_items", ["id"], unique=False)
    op.create_index(op.f("ix_online_order_items_order_id"), "online_order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_online_order_items_variant_id"), "online_order_items", ["variant_id"], unique=False)

    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_jalali_date", sa.String(length=10), nullable=True),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["online_channels.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["online_orders.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_reservations_channel_id"), "stock_reservations", ["channel_id"], unique=False)
    op.create_index(op.f("ix_stock_reservations_expires_jalali_date"), "stock_reservations", ["expires_jalali_date"], unique=False)
    op.create_index(op.f("ix_stock_reservations_id"), "stock_reservations", ["id"], unique=False)
    op.create_index(op.f("ix_stock_reservations_order_id"), "stock_reservations", ["order_id"], unique=False)
    op.create_index(op.f("ix_stock_reservations_status"), "stock_reservations", ["status"], unique=False)
    op.create_index(op.f("ix_stock_reservations_variant_id"), "stock_reservations", ["variant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_reservations_variant_id"), table_name="stock_reservations")
    op.drop_index(op.f("ix_stock_reservations_status"), table_name="stock_reservations")
    op.drop_index(op.f("ix_stock_reservations_order_id"), table_name="stock_reservations")
    op.drop_index(op.f("ix_stock_reservations_id"), table_name="stock_reservations")
    op.drop_index(op.f("ix_stock_reservations_expires_jalali_date"), table_name="stock_reservations")
    op.drop_index(op.f("ix_stock_reservations_channel_id"), table_name="stock_reservations")
    op.drop_table("stock_reservations")
    op.drop_index(op.f("ix_online_order_items_variant_id"), table_name="online_order_items")
    op.drop_index(op.f("ix_online_order_items_order_id"), table_name="online_order_items")
    op.drop_index(op.f("ix_online_order_items_id"), table_name="online_order_items")
    op.drop_table("online_order_items")
    op.drop_index(op.f("ix_online_price_rules_variant_id"), table_name="online_price_rules")
    op.drop_index(op.f("ix_online_price_rules_starts_jalali_date"), table_name="online_price_rules")
    op.drop_index(op.f("ix_online_price_rules_id"), table_name="online_price_rules")
    op.drop_index(op.f("ix_online_price_rules_ends_jalali_date"), table_name="online_price_rules")
    op.drop_index(op.f("ix_online_price_rules_channel_id"), table_name="online_price_rules")
    op.drop_table("online_price_rules")
    op.drop_index(op.f("ix_online_orders_status"), table_name="online_orders")
    op.drop_index(op.f("ix_online_orders_jalali_date"), table_name="online_orders")
    op.drop_index(op.f("ix_online_orders_id"), table_name="online_orders")
    op.drop_index(op.f("ix_online_orders_external_order_id"), table_name="online_orders")
    op.drop_index(op.f("ix_online_orders_channel_id"), table_name="online_orders")
    op.drop_table("online_orders")
    op.drop_index(op.f("ix_online_channels_token_hash"), table_name="online_channels")
    op.drop_index(op.f("ix_online_channels_name"), table_name="online_channels")
    op.drop_index(op.f("ix_online_channels_id"), table_name="online_channels")
    op.drop_table("online_channels")
