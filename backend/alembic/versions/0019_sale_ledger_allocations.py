"""make sale receivables canonical and record settlement allocations

Revision ID: 0019_sale_ledger_allocations
Revises: 0018_payment_due_audits
Create Date: 2026-09-09
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0019_sale_ledger_allocations"
down_revision: str | None = "0018_payment_due_audits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            """SELECT source_id FROM ledger_entries
               WHERE source_type = 'sale' AND source_id IS NOT NULL
               GROUP BY source_id HAVING COUNT(*) > 1 LIMIT 1"""
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            f"Duplicate sale ledger source_id={duplicate[0]}; resolve explicitly before migration"
        )

    op.create_index(
        "uq_ledger_entries_sale_source",
        "ledger_entries",
        ["source_type", "source_id"],
        unique=True,
        sqlite_where=sa.text("source_type = 'sale' AND source_id IS NOT NULL"),
        postgresql_where=sa.text("source_type = 'sale' AND source_id IS NOT NULL"),
    )
    op.create_table(
        "settlement_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=False),
        sa.Column("amount_rial", sa.Integer(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_rial > 0", name="ck_settlement_allocations_amount_positive"),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.ForeignKeyConstraint(["settlement_id"], ["settlements.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_settlement_allocations_id"), "settlement_allocations", ["id"])
    op.create_index(
        op.f("ix_settlement_allocations_ledger_entry_id"),
        "settlement_allocations",
        ["ledger_entry_id"],
    )
    op.create_index(
        op.f("ix_settlement_allocations_settlement_id"),
        "settlement_allocations",
        ["settlement_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_settlement_allocations_settlement_id"), table_name="settlement_allocations")
    op.drop_index(op.f("ix_settlement_allocations_ledger_entry_id"), table_name="settlement_allocations")
    op.drop_index(op.f("ix_settlement_allocations_id"), table_name="settlement_allocations")
    op.drop_table("settlement_allocations")
    op.drop_index("uq_ledger_entries_sale_source", table_name="ledger_entries")
