"""add user token version

Revision ID: 0009_user_token_version
Revises: 0008_bale_customer_login
Create Date: 2026-09-06
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0009_user_token_version"
down_revision: str | None = "0008_bale_customer_login"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "token_version")
