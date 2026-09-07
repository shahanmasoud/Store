"""add append-only cheque audit history

Revision ID: 0015_cheque_audits
Revises: 0014_ledger_due_dates
Create Date: 2026-09-08
"""
from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "0015_cheque_audits"
down_revision: str | None = "0014_ledger_due_dates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cheque_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cheque_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=True),
        sa.Column("actor_full_name", sa.String(length=120), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["cheque_id"], ["cheques.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cheque_audits_action"), "cheque_audits", ["action"])
    op.create_index(op.f("ix_cheque_audits_actor_user_id"), "cheque_audits", ["actor_user_id"])
    op.create_index(op.f("ix_cheque_audits_cheque_id"), "cheque_audits", ["cheque_id"])
    op.create_index(op.f("ix_cheque_audits_id"), "cheque_audits", ["id"])

    connection = op.get_bind()
    # Every cheque needs a stable concurrency token. Existing timestamps are preserved.
    connection.execute(
        sa.text("UPDATE cheques SET updated_at_utc = created_at_utc WHERE updated_at_utc IS NULL")
    )
    rows = connection.execute(
        sa.text(
            """
            SELECT id, cheque_type, person_id, bank_name, cheque_number, amount_rial,
                   issue_jalali_date, due_jalali_date, status, note, is_active,
                   created_at_utc, updated_at_utc
            FROM cheques ORDER BY id
            """
        )
    ).mappings()
    audit_table = sa.table(
        "cheque_audits",
        sa.column("cheque_id", sa.Integer()),
        sa.column("action", sa.String()),
        sa.column("actor_user_id", sa.Integer()),
        sa.column("actor_username", sa.String()),
        sa.column("actor_full_name", sa.String()),
        sa.column("before_json", sa.JSON()),
        sa.column("after_json", sa.JSON()),
        sa.column("reason", sa.Text()),
        sa.column("occurred_at_utc", sa.DateTime(timezone=True)),
    )
    legacy_audits = []
    for row in rows:
        snapshot = {
            "id": row["id"],
            "cheque_type": row["cheque_type"],
            "person_id": row["person_id"],
            "bank_name": row["bank_name"],
            "cheque_number": row["cheque_number"],
            "amount_rial": row["amount_rial"],
            "issue_jalali_date": row["issue_jalali_date"],
            "due_jalali_date": row["due_jalali_date"],
            "status": row["status"],
            "note": row["note"],
            "is_active": bool(row["is_active"]),
        }
        occurred_at = row["created_at_utc"] or row["updated_at_utc"] or datetime.now(timezone.utc)
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)
        legacy_audits.append(
            {
                "cheque_id": row["id"],
                "action": "legacy_snapshot",
                "actor_user_id": None,
                "actor_username": None,
                "actor_full_name": None,
                "before_json": None,
                "after_json": snapshot,
                "reason": "تصویر اولیه رکورد موجود پیش از فعال‌سازی ممیزی چک",
                "occurred_at_utc": occurred_at,
            }
        )
    if legacy_audits:
        op.bulk_insert(audit_table, legacy_audits)


def downgrade() -> None:
    op.drop_index(op.f("ix_cheque_audits_id"), table_name="cheque_audits")
    op.drop_index(op.f("ix_cheque_audits_cheque_id"), table_name="cheque_audits")
    op.drop_index(op.f("ix_cheque_audits_actor_user_id"), table_name="cheque_audits")
    op.drop_index(op.f("ix_cheque_audits_action"), table_name="cheque_audits")
    op.drop_table("cheque_audits")
