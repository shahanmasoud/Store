"""add explicit ledger due dates and append-only audit

Revision ID: 0014_ledger_due_dates
Revises: 0013_product_image
Create Date: 2026-09-07
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0014_ledger_due_dates"
down_revision: str | None = "0013_product_image"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing entries intentionally remain NULL; their posting date is not a safe due-date guess.
    with op.batch_alter_table("ledger_entries") as batch_op:
        batch_op.add_column(sa.Column("due_jalali_date", sa.String(length=10), nullable=True))
        batch_op.create_index(op.f("ix_ledger_entries_due_jalali_date"), ["due_jalali_date"], unique=False)

    op.create_table(
        "ledger_due_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=True),
        sa.Column("actor_full_name", sa.String(length=120), nullable=True),
        sa.Column("before_due_date", sa.String(length=10), nullable=True),
        sa.Column("after_due_date", sa.String(length=10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_due_audits_actor_user_id"), "ledger_due_audits", ["actor_user_id"])
    op.create_index(op.f("ix_ledger_due_audits_entry_id"), "ledger_due_audits", ["entry_id"])
    op.create_index(op.f("ix_ledger_due_audits_id"), "ledger_due_audits", ["id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_due_audits_id"), table_name="ledger_due_audits")
    op.drop_index(op.f("ix_ledger_due_audits_entry_id"), table_name="ledger_due_audits")
    op.drop_index(op.f("ix_ledger_due_audits_actor_user_id"), table_name="ledger_due_audits")
    op.drop_table("ledger_due_audits")
    with op.batch_alter_table("ledger_entries") as batch_op:
        batch_op.drop_index(op.f("ix_ledger_entries_due_jalali_date"))
        batch_op.drop_column("due_jalali_date")
