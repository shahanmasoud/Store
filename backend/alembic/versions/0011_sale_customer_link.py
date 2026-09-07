"""link sale invoices to persons

Revision ID: 0011_sale_customer_link
Revises: 0010_person_customer_details
Create Date: 2026-09-07
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011_sale_customer_link"
down_revision: str | None = "0010_person_customer_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sale_invoices") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_sale_invoices_customer_id_persons",
            "persons",
            ["customer_id"],
            ["id"],
        )
        batch_op.create_index(op.f("ix_sale_invoices_customer_id"), ["customer_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("sale_invoices") as batch_op:
        batch_op.drop_index(op.f("ix_sale_invoices_customer_id"))
        batch_op.drop_constraint("fk_sale_invoices_customer_id_persons", type_="foreignkey")
        batch_op.drop_column("customer_id")
