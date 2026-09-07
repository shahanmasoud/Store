"""add product image filename

Revision ID: 0013_product_image
Revises: 0012_inventory_adjustment_audit
Create Date: 2026-09-07
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0013_product_image"
down_revision: str | None = "0012_inventory_adjustment_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("image_filename", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("image_filename")
