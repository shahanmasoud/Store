"""store encrypted Bale bot configuration

Revision ID: 0021_bale_bot_configuration
Revises: 0020_variant_images
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0021_bale_bot_configuration"
down_revision: str | None = "0020_variant_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bale_bot_configurations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_ciphertext", sa.Text(), nullable=False),
        sa.Column("webhook_secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("bot_username", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("bale_bot_configurations")
