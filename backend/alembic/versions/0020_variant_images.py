"""store images independently for each sellable variant

Revision ID: 0020_variant_images
Revises: 0019_sale_ledger_allocations
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0020_variant_images"
down_revision: str | None = "0019_sale_ledger_allocations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product_variants", sa.Column("image_filename", sa.String(length=255), nullable=True))
    # A legacy shared image is assigned to one item only; future uploads are independent.
    op.execute(
        """UPDATE product_variants
           SET image_filename = (
               SELECT products.image_filename FROM products
               WHERE products.id = product_variants.product_id
           )
           WHERE id IN (
               SELECT MIN(pv.id) FROM product_variants pv
               JOIN products p ON p.id = pv.product_id
               WHERE p.image_filename IS NOT NULL
               GROUP BY pv.product_id
           )"""
    )
    op.execute("UPDATE products SET image_filename = NULL WHERE image_filename IS NOT NULL")


def downgrade() -> None:
    op.execute(
        """UPDATE products
           SET image_filename = (
               SELECT pv.image_filename FROM product_variants pv
               WHERE pv.product_id = products.id AND pv.image_filename IS NOT NULL
               ORDER BY pv.id LIMIT 1
           )
           WHERE EXISTS (
               SELECT 1 FROM product_variants pv
               WHERE pv.product_id = products.id AND pv.image_filename IS NOT NULL
           )"""
    )
    op.drop_column("product_variants", "image_filename")
