"""ledger cheques dues tables

Revision ID: 0004_ledger_cheques_dues_tables
Revises: 0003_purchases_inventory_tables
Create Date: 2026-08-24
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_ledger_cheques_dues_tables"
down_revision: str | None = "0003_purchases_inventory_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("person_type", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_persons_id"), "persons", ["id"], unique=False)
    op.create_index(op.f("ix_persons_name"), "persons", ["name"], unique=False)
    op.create_index(op.f("ix_persons_person_type"), "persons", ["person_type"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("amount_rial", sa.Integer(), nullable=False),
        sa.Column("remaining_rial", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_entry_type"), "ledger_entries", ["entry_type"], unique=False)
    op.create_index(op.f("ix_ledger_entries_id"), "ledger_entries", ["id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_jalali_date"), "ledger_entries", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_ledger_entries_person_id"), "ledger_entries", ["person_id"], unique=False)
    op.create_index(op.f("ix_ledger_entries_source_type"), "ledger_entries", ["source_type"], unique=False)
    op.create_index(op.f("ix_ledger_entries_status"), "ledger_entries", ["status"], unique=False)

    op.create_table(
        "settlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("amount_rial", sa.Integer(), nullable=False),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_settlements_id"), "settlements", ["id"], unique=False)
    op.create_index(op.f("ix_settlements_jalali_date"), "settlements", ["jalali_date"], unique=False)
    op.create_index(op.f("ix_settlements_person_id"), "settlements", ["person_id"], unique=False)

    op.create_table(
        "cheques",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cheque_type", sa.String(length=20), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=True),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("cheque_number", sa.String(length=80), nullable=False),
        sa.Column("amount_rial", sa.Integer(), nullable=False),
        sa.Column("issue_jalali_date", sa.String(length=10), nullable=False),
        sa.Column("due_jalali_date", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cheques_cheque_number"), "cheques", ["cheque_number"], unique=False)
    op.create_index(op.f("ix_cheques_cheque_type"), "cheques", ["cheque_type"], unique=False)
    op.create_index(op.f("ix_cheques_due_jalali_date"), "cheques", ["due_jalali_date"], unique=False)
    op.create_index(op.f("ix_cheques_id"), "cheques", ["id"], unique=False)
    op.create_index(op.f("ix_cheques_person_id"), "cheques", ["person_id"], unique=False)
    op.create_index(op.f("ix_cheques_status"), "cheques", ["status"], unique=False)

    op.create_table(
        "cheque_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cheque_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("jalali_date", sa.String(length=10), nullable=False),
        sa.Column("local_time", sa.String(length=5), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cheque_id"], ["cheques.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cheque_events_cheque_id"), "cheque_events", ["cheque_id"], unique=False)
    op.create_index(op.f("ix_cheque_events_event_type"), "cheque_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_cheque_events_id"), "cheque_events", ["id"], unique=False)
    op.create_index(op.f("ix_cheque_events_jalali_date"), "cheque_events", ["jalali_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cheque_events_jalali_date"), table_name="cheque_events")
    op.drop_index(op.f("ix_cheque_events_id"), table_name="cheque_events")
    op.drop_index(op.f("ix_cheque_events_event_type"), table_name="cheque_events")
    op.drop_index(op.f("ix_cheque_events_cheque_id"), table_name="cheque_events")
    op.drop_table("cheque_events")
    op.drop_index(op.f("ix_cheques_status"), table_name="cheques")
    op.drop_index(op.f("ix_cheques_person_id"), table_name="cheques")
    op.drop_index(op.f("ix_cheques_id"), table_name="cheques")
    op.drop_index(op.f("ix_cheques_due_jalali_date"), table_name="cheques")
    op.drop_index(op.f("ix_cheques_cheque_type"), table_name="cheques")
    op.drop_index(op.f("ix_cheques_cheque_number"), table_name="cheques")
    op.drop_table("cheques")
    op.drop_index(op.f("ix_settlements_person_id"), table_name="settlements")
    op.drop_index(op.f("ix_settlements_jalali_date"), table_name="settlements")
    op.drop_index(op.f("ix_settlements_id"), table_name="settlements")
    op.drop_table("settlements")
    op.drop_index(op.f("ix_ledger_entries_status"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_source_type"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_person_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_jalali_date"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_id"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_entry_type"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(op.f("ix_persons_person_type"), table_name="persons")
    op.drop_index(op.f("ix_persons_name"), table_name="persons")
    op.drop_index(op.f("ix_persons_id"), table_name="persons")
    op.drop_table("persons")
