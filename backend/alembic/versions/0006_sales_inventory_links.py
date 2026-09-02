"""link sales to inventory transactions

Revision ID: 0006_sales_inventory_links
Revises: 0005_online_integration_tables
Create Date: 2026-09-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006_sales_inventory_links"
down_revision: str | None = "0005_online_integration_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_transactions") as batch_op:
        batch_op.add_column(sa.Column("sale_invoice_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sale_invoice_item_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_inventory_transactions_sale_invoice_id",
            "sale_invoices",
            ["sale_invoice_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_inventory_transactions_sale_invoice_item_id",
            "sale_invoice_items",
            ["sale_invoice_item_id"],
            ["id"],
        )
        batch_op.create_index("ix_inventory_transactions_sale_invoice_id", ["sale_invoice_id"])
        batch_op.create_index("ix_inventory_transactions_sale_invoice_item_id", ["sale_invoice_item_id"])


def downgrade() -> None:
    with op.batch_alter_table("inventory_transactions") as batch_op:
        batch_op.drop_index("ix_inventory_transactions_sale_invoice_item_id")
        batch_op.drop_index("ix_inventory_transactions_sale_invoice_id")
        batch_op.drop_constraint("fk_inventory_transactions_sale_invoice_item_id", type_="foreignkey")
        batch_op.drop_constraint("fk_inventory_transactions_sale_invoice_id", type_="foreignkey")
        batch_op.drop_column("sale_invoice_item_id")
        batch_op.drop_column("sale_invoice_id")
