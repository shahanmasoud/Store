"""add audited sale payment due-date editing

Revision ID: 0018_payment_due_audits
Revises: 0017_ledger_action_audits
Create Date: 2026-09-09
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0018_payment_due_audits"
down_revision: str | None = "0017_ledger_action_audits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_due_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=True),
        sa.Column("actor_full_name", sa.String(length=120), nullable=True),
        sa.Column("before_due_date", sa.String(length=10), nullable=True),
        sa.Column("after_due_date", sa.String(length=10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_due_audits_id"), "payment_due_audits", ["id"])
    op.create_index(op.f("ix_payment_due_audits_payment_id"), "payment_due_audits", ["payment_id"])
    op.create_index(op.f("ix_payment_due_audits_actor_user_id"), "payment_due_audits", ["actor_user_id"])

    # Existing payments need a stable token before optimistic updates are accepted.
    op.execute("UPDATE payments SET updated_at_utc = created_at_utc WHERE updated_at_utc IS NULL")


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_due_audits_actor_user_id"), table_name="payment_due_audits")
    op.drop_index(op.f("ix_payment_due_audits_payment_id"), table_name="payment_due_audits")
    op.drop_index(op.f("ix_payment_due_audits_id"), table_name="payment_due_audits")
    op.drop_table("payment_due_audits")
