"""add append-only audit history for ledger operations

Revision ID: 0017_ledger_action_audits
Revises: 0016_user_permissions
Create Date: 2026-09-08
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0017_ledger_action_audits"
down_revision: str | None = "0016_user_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ledger_action_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=True),
        sa.Column("actor_full_name", sa.String(length=120), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_action_audits_id"), "ledger_action_audits", ["id"])
    op.create_index("ix_ledger_action_audits_entity", "ledger_action_audits", ["entity_type", "entity_id"])
    op.create_index(op.f("ix_ledger_action_audits_actor_user_id"), "ledger_action_audits", ["actor_user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ledger_action_audits_actor_user_id"), table_name="ledger_action_audits")
    op.drop_index("ix_ledger_action_audits_entity", table_name="ledger_action_audits")
    op.drop_index(op.f("ix_ledger_action_audits_id"), table_name="ledger_action_audits")
    op.drop_table("ledger_action_audits")
