"""add sub-admin permissions and user administration audits

Revision ID: 0016_user_permissions
Revises: 0015_cheque_audits
Create Date: 2026-09-08
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0016_user_permissions"
down_revision: str | None = "0015_cheque_audits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("can_sales", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("can_catalog_inventory", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("can_ledger", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("can_cheques_reports", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "user_admin_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_admin_audits_action"), "user_admin_audits", ["action"])
    op.create_index(op.f("ix_user_admin_audits_actor_user_id"), "user_admin_audits", ["actor_user_id"])
    op.create_index(op.f("ix_user_admin_audits_id"), "user_admin_audits", ["id"])
    op.create_index(op.f("ix_user_admin_audits_target_user_id"), "user_admin_audits", ["target_user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_user_admin_audits_target_user_id"), table_name="user_admin_audits")
    op.drop_index(op.f("ix_user_admin_audits_id"), table_name="user_admin_audits")
    op.drop_index(op.f("ix_user_admin_audits_actor_user_id"), table_name="user_admin_audits")
    op.drop_index(op.f("ix_user_admin_audits_action"), table_name="user_admin_audits")
    op.drop_table("user_admin_audits")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("can_cheques_reports")
        batch_op.drop_column("can_ledger")
        batch_op.drop_column("can_catalog_inventory")
        batch_op.drop_column("can_sales")
