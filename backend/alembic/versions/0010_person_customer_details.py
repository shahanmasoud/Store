"""add customer details to persons

Revision ID: 0010_person_customer_details
Revises: 0009_user_token_version
Create Date: 2026-09-06
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010_person_customer_details"
down_revision: str | None = "0009_user_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("persons", sa.Column("note", sa.Text(), nullable=True))
    op.add_column(
        "persons",
        sa.Column("credit_status", sa.String(length=20), nullable=False, server_default="normal"),
    )
    op.create_index(op.f("ix_persons_credit_status"), "persons", ["credit_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_persons_credit_status"), table_name="persons")
    with op.batch_alter_table("persons") as batch_op:
        batch_op.drop_column("credit_status")
        batch_op.drop_column("note")
