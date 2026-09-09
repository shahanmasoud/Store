"""Read-only audit of legacy sale receivables against canonical ledger entries.

This command intentionally cannot backfill or repair data.  It opens SQLite in
read-only mode and emits a deterministic, privacy-minimal JSON report suitable
for review before a separate, explicitly approved reconciliation phase.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.scripts.sqlite_backup import sqlite_path_from_url


REPORT_SCHEMA_VERSION = 1
EXIT_CLEAN = 0
EXIT_OPERATIONAL_ERROR = 1
EXIT_RECONCILIATION_REQUIRED = 2


def _reason(code: str, expected: Any, actual: Any) -> dict[str, Any]:
    return {"code": code, "expected": expected, "actual": actual}


def _expected_due_date(connection: sqlite3.Connection, invoice_id: int) -> str | None:
    row = connection.execute(
        """SELECT MIN(due_jalali_date)
           FROM payments
           WHERE invoice_id = ? AND status = 'pending' AND due_jalali_date IS NOT NULL""",
        (invoice_id,),
    ).fetchone()
    return row[0] if row else None


def _entry_reasons(
    connection: sqlite3.Connection,
    invoice: sqlite3.Row,
    entry: sqlite3.Row,
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    checks = (
        ("person_id", invoice["customer_id"], entry["person_id"]),
        ("entry_type", "debit", entry["entry_type"]),
        ("amount_rial", invoice["due_total_rial"], entry["amount_rial"]),
        ("jalali_date", invoice["jalali_date"], entry["jalali_date"]),
        ("local_time", invoice["local_time"], entry["local_time"]),
        ("due_jalali_date", _expected_due_date(connection, invoice["id"]), entry["due_jalali_date"]),
    )
    for field, expected, actual in checks:
        if expected != actual:
            reasons.append(_reason(f"{field}_mismatch", expected, actual))

    remaining = entry["remaining_rial"]
    amount = entry["amount_rial"]
    allocated = connection.execute(
        "SELECT COALESCE(SUM(amount_rial), 0) FROM settlement_allocations WHERE ledger_entry_id = ?",
        (entry["id"],),
    ).fetchone()[0]
    if remaining < 0 or remaining > amount:
        reasons.append(_reason("remaining_out_of_range", f"0..{amount}", remaining))
    if allocated != amount - remaining:
        reasons.append(_reason("allocation_mismatch", amount - remaining, allocated))
    expected_status = "settled" if remaining == 0 else "open"
    if entry["status"] != expected_status:
        reasons.append(_reason("status_mismatch", expected_status, entry["status"]))
    if not bool(entry["is_active"]):
        reasons.append(_reason("is_active_mismatch", True, False))
    return reasons


def _canceled_entry_reasons(
    connection: sqlite3.Connection,
    invoice: sqlite3.Row,
    entry: sqlite3.Row,
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    checks = (
        ("person_id", invoice["customer_id"], entry["person_id"]),
        ("entry_type", "debit", entry["entry_type"]),
        ("amount_rial", invoice["due_total_rial"], entry["amount_rial"]),
        ("jalali_date", invoice["jalali_date"], entry["jalali_date"]),
        ("local_time", invoice["local_time"], entry["local_time"]),
        ("due_jalali_date", _expected_due_date(connection, invoice["id"]), entry["due_jalali_date"]),
        ("remaining_rial", 0, entry["remaining_rial"]),
        ("status", "canceled", entry["status"]),
        ("is_active", False, bool(entry["is_active"])),
    )
    for field, expected, actual in checks:
        if expected != actual:
            reasons.append(_reason(f"{field}_mismatch", expected, actual))
    allocated = connection.execute(
        "SELECT COALESCE(SUM(amount_rial), 0) FROM settlement_allocations WHERE ledger_entry_id = ?",
        (entry["id"],),
    ).fetchone()[0]
    if allocated != 0:
        reasons.append(_reason("canceled_entry_has_allocation", 0, allocated))
    return reasons


def build_report(connection: sqlite3.Connection) -> dict[str, Any]:
    """Build a stable report using IDs and financial facts only (no PII)."""
    connection.row_factory = sqlite3.Row
    invoices = connection.execute(
        """SELECT id, customer_id, due_total_rial, jalali_date, local_time, status, is_active
           FROM sale_invoices ORDER BY id"""
    ).fetchall()
    entries = connection.execute(
        """SELECT id, person_id, entry_type, amount_rial, remaining_rial, source_id,
                  jalali_date, due_jalali_date, local_time, status, is_active
           FROM ledger_entries
           WHERE source_type = 'sale' AND source_id IS NOT NULL
           ORDER BY source_id, id"""
    ).fetchall()
    entries_by_source: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for entry in entries:
        entries_by_source[entry["source_id"]].append(entry)

    missing: list[dict[str, Any]] = []
    exact: list[dict[str, Any]] = []
    conflict: list[dict[str, Any]] = []
    known_invoice_ids = {invoice["id"] for invoice in invoices}
    eligible_ids: set[int] = set()

    for invoice in invoices:
        eligible = (
            bool(invoice["is_active"])
            and invoice["status"] == "active"
            and invoice["customer_id"] is not None
            and invoice["due_total_rial"] > 0
        )
        linked = entries_by_source.get(invoice["id"], [])
        if not eligible:
            if linked:
                if (
                    invoice["status"] == "canceled"
                    and not bool(invoice["is_active"])
                    and invoice["customer_id"] is not None
                    and invoice["due_total_rial"] > 0
                    and len(linked) == 1
                ):
                    canceled_reasons = _canceled_entry_reasons(connection, invoice, linked[0])
                    if not canceled_reasons:
                        continue
                else:
                    canceled_reasons = [{"code": "ineligible_invoice_has_sale_entry"}]
                conflict.append(
                    {
                        "invoice_id": invoice["id"],
                        "ledger_entry_ids": [entry["id"] for entry in linked],
                        "reasons": canceled_reasons,
                    }
                )
            continue
        eligible_ids.add(invoice["id"])
        if not linked:
            missing.append(
                {
                    "invoice_id": invoice["id"],
                    "customer_id": invoice["customer_id"],
                    "due_total_rial": invoice["due_total_rial"],
                }
            )
            continue
        if len(linked) != 1:
            conflict.append(
                {
                    "invoice_id": invoice["id"],
                    "ledger_entry_ids": [entry["id"] for entry in linked],
                    "reasons": [_reason("sale_entry_count", 1, len(linked))],
                }
            )
            continue
        entry = linked[0]
        reasons = _entry_reasons(connection, invoice, entry)
        item = {"invoice_id": invoice["id"], "ledger_entry_id": entry["id"]}
        if reasons:
            conflict.append({**item, "reasons": reasons})
        else:
            exact.append(item)

    for source_id, linked in entries_by_source.items():
        if source_id not in known_invoice_ids:
            conflict.append(
                {
                    "invoice_id": source_id,
                    "ledger_entry_ids": [entry["id"] for entry in linked],
                    "reasons": [{"code": "sale_source_invoice_missing"}],
                }
            )

    conflict.sort(key=lambda item: (item["invoice_id"], item.get("ledger_entry_id", -1)))
    groups = {"missing": missing, "exact": exact, "conflict": conflict}
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "dry-run",
        "read_only": True,
        "summary": {
            "eligible_sales": len(eligible_ids),
            "missing": len(missing),
            "exact": len(exact),
            "conflict": len(conflict),
        },
        "groups": groups,
    }


def audit_database(database_path: Path) -> dict[str, Any]:
    path = database_path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError("SQLite database does not exist")
    uri = f"{path.as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        return build_report(connection)
    finally:
        connection.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run audit of sale ledger reconciliation")
    parser.add_argument(
        "--database-url",
        default=None,
        help="File-based SQLite URL; defaults to DATABASE_URL (never printed)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        database_url = args.database_url or get_settings().database_url
        report = audit_database(sqlite_path_from_url(database_url))
    except Exception as exc:
        # Operational output deliberately excludes exception text and paths.
        print(json.dumps({"schema_version": REPORT_SCHEMA_VERSION, "error": type(exc).__name__}, sort_keys=True))
        return EXIT_OPERATIONAL_ERROR
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if report["summary"]["missing"] or report["summary"]["conflict"]:
        return EXIT_RECONCILIATION_REQUIRED
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
