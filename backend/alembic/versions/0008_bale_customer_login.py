"""add Bale customer login tables

Revision ID: 0008_bale_customer_login
Revises: 0007_settlement_entry_type
Create Date: 2026-09-04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008_bale_customer_login"
down_revision: str | None = "0007_settlement_entry_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_user_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("provider_username", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_customer_provider_identity"),
    )
    op.create_index(op.f("ix_customer_accounts_id"), "customer_accounts", ["id"], unique=False)

    op.create_table(
        "bale_login_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("return_path", sa.String(length=255), nullable=False),
        sa.Column("bale_user_id", sa.String(length=64), nullable=True),
        sa.Column("bale_display_name", sa.String(length=120), nullable=True),
        sa.Column("bale_username", sa.String(length=120), nullable=True),
        sa.Column("customer_account_id", sa.Integer(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_account_id"], ["customer_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bale_login_challenges_customer_account_id"), "bale_login_challenges", ["customer_account_id"], unique=False)
    op.create_index(op.f("ix_bale_login_challenges_expires_at_utc"), "bale_login_challenges", ["expires_at_utc"], unique=False)
    op.create_index(op.f("ix_bale_login_challenges_status"), "bale_login_challenges", ["status"], unique=False)
    op.create_index("ix_bale_login_challenges_code_hash_status", "bale_login_challenges", ["code_hash", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bale_login_challenges_code_hash_status", table_name="bale_login_challenges")
    op.drop_index(op.f("ix_bale_login_challenges_status"), table_name="bale_login_challenges")
    op.drop_index(op.f("ix_bale_login_challenges_expires_at_utc"), table_name="bale_login_challenges")
    op.drop_index(op.f("ix_bale_login_challenges_customer_account_id"), table_name="bale_login_challenges")
    op.drop_table("bale_login_challenges")
    op.drop_index(op.f("ix_customer_accounts_id"), table_name="customer_accounts")
    op.drop_table("customer_accounts")
