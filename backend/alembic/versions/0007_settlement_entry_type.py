"""add settlement entry type

Revision ID: 0007_settlement_entry_type
Revises: 0006_sales_inventory_links
Create Date: 2026-09-03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_settlement_entry_type"
down_revision: str | None = "0006_sales_inventory_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("settlements") as batch_op:
        batch_op.add_column(sa.Column("entry_type", sa.String(length=20), nullable=False, server_default="debit"))
        batch_op.create_index("ix_settlements_entry_type", ["entry_type"])


def downgrade() -> None:
    with op.batch_alter_table("settlements") as batch_op:
        batch_op.drop_index("ix_settlements_entry_type")
        batch_op.drop_column("entry_type")
