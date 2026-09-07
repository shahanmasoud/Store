"""add inventory adjustment audit fields

Revision ID: 0012_inventory_adjustment_audit
Revises: 0011_sale_customer_link
Create Date: 2026-09-07
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0012_inventory_adjustment_audit"
down_revision: str | None = "0011_sale_customer_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # All fields stay nullable so existing purchase/sale history migrates intact.
    with op.batch_alter_table("inventory_transactions") as batch_op:
        batch_op.add_column(sa.Column("adjustment_type", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("actor_username", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("actor_full_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("quantity_balance_after", sa.Numeric(12, 3), nullable=True))
        batch_op.add_column(sa.Column("weighted_average_cost_after_rial", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_inventory_transactions_actor_user_id_users",
            "users",
            ["actor_user_id"],
            ["id"],
        )
        batch_op.create_index(op.f("ix_inventory_transactions_adjustment_type"), ["adjustment_type"], unique=False)
        batch_op.create_index(op.f("ix_inventory_transactions_actor_user_id"), ["actor_user_id"], unique=False)

    # Preserve existing inventory as authoritative while making any historical
    # discrepancy explicit. No balance is overwritten or silently discarded.
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE inventory_transactions SET occurred_at_utc = created_at_utc WHERE occurred_at_utc IS NULL")
    )
    inventory_rows = connection.execute(
        sa.text(
            """
            SELECT i.variant_id, i.quantity_on_hand, i.weighted_average_cost_rial,
                   COALESCE(SUM(t.quantity_delta), 0) AS transaction_balance
            FROM inventory_items AS i
            LEFT JOIN inventory_transactions AS t ON t.variant_id = i.variant_id
            GROUP BY i.variant_id, i.quantity_on_hand, i.weighted_average_cost_rial
            """
        )
    ).mappings()
    for row in inventory_rows:
        delta = row["quantity_on_hand"] - row["transaction_balance"]
        if delta == 0:
            continue
        latest = connection.execute(
            sa.text(
                """
                SELECT jalali_date, local_time
                FROM inventory_transactions
                WHERE variant_id = :variant_id
                ORDER BY id DESC LIMIT 1
                """
            ),
            {"variant_id": row["variant_id"]},
        ).mappings().first()
        connection.execute(
            sa.text(
                """
                INSERT INTO inventory_transactions
                    (variant_id, transaction_type, adjustment_type, quantity_delta,
                     quantity_balance_after, unit_cost_rial, weighted_average_cost_after_rial,
                     jalali_date, local_time, note, reason, occurred_at_utc, created_at_utc)
                VALUES
                    (:variant_id, 'opening_reconciliation', NULL, :delta,
                     :balance, :unit_cost, :unit_cost,
                     :jalali_date, :local_time, :reason, :reason, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "variant_id": row["variant_id"],
                "delta": delta,
                "balance": row["quantity_on_hand"],
                "unit_cost": row["weighted_average_cost_rial"],
                "jalali_date": latest["jalali_date"] if latest else "نامشخص",
                "local_time": latest["local_time"] if latest else "--:--",
                "reason": "تطبیق خودکار مانده موجودی هنگام ارتقای دیتابیس",
            },
        )

    with op.batch_alter_table("inventory_transactions") as batch_op:
        batch_op.alter_column("occurred_at_utc", existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("inventory_transactions") as batch_op:
        batch_op.drop_index(op.f("ix_inventory_transactions_actor_user_id"))
        batch_op.drop_index(op.f("ix_inventory_transactions_adjustment_type"))
        batch_op.drop_constraint("fk_inventory_transactions_actor_user_id_users", type_="foreignkey")
        batch_op.drop_column("occurred_at_utc")
        batch_op.drop_column("weighted_average_cost_after_rial")
        batch_op.drop_column("quantity_balance_after")
        batch_op.drop_column("reason")
        batch_op.drop_column("actor_full_name")
        batch_op.drop_column("actor_username")
        batch_op.drop_column("actor_user_id")
        batch_op.drop_column("adjustment_type")
