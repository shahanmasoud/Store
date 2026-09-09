import hashlib
import json
import sqlite3
from pathlib import Path

from app.scripts import reconcile_sale_ledger


def _database(tmp_path: Path, name: str = "legacy.db") -> Path:
    path = tmp_path / name
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE sale_invoices (
              id INTEGER PRIMARY KEY, customer_id INTEGER, due_total_rial INTEGER NOT NULL,
              jalali_date TEXT NOT NULL, local_time TEXT NOT NULL,
              status TEXT NOT NULL, is_active INTEGER NOT NULL
            );
            CREATE TABLE payments (
              id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL, status TEXT NOT NULL,
              due_jalali_date TEXT
            );
            CREATE TABLE ledger_entries (
              id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL, entry_type TEXT NOT NULL,
              amount_rial INTEGER NOT NULL, remaining_rial INTEGER NOT NULL,
              source_type TEXT NOT NULL, source_id INTEGER,
              jalali_date TEXT NOT NULL, due_jalali_date TEXT, local_time TEXT NOT NULL,
              status TEXT NOT NULL, is_active INTEGER NOT NULL
            );
            CREATE TABLE settlement_allocations (
              id INTEGER PRIMARY KEY, settlement_id INTEGER NOT NULL,
              ledger_entry_id INTEGER NOT NULL, amount_rial INTEGER NOT NULL
            );
            """
        )
    return path


def _sale(connection: sqlite3.Connection, invoice_id: int, customer_id: int = 10, due: int = 900) -> None:
    connection.execute(
        "INSERT INTO sale_invoices VALUES (?, ?, ?, '1405/06/01', '10:00', 'active', 1)",
        (invoice_id, customer_id, due),
    )
    connection.execute("INSERT INTO payments VALUES (?, ?, 'pending', '1405/06/20')", (invoice_id, invoice_id))


def _ledger(
    connection: sqlite3.Connection,
    entry_id: int,
    source_id: int | None,
    *,
    person_id: int = 10,
    amount: int = 900,
    remaining: int = 900,
    source_type: str = "sale",
) -> None:
    connection.execute(
        """INSERT INTO ledger_entries VALUES
           (?, ?, 'debit', ?, ?, ?, ?, '1405/06/01', '1405/06/20', '10:00', 'open', 1)""",
        (entry_id, person_id, amount, remaining, source_type, source_id),
    )


def test_report_is_deterministic_and_database_bytes_and_rows_do_not_change(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        _sale(connection, 1)
        _ledger(connection, 1, 1)
        before_rows = connection.execute("SELECT * FROM ledger_entries").fetchall()
    before_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    first = reconcile_sale_ledger.audit_database(path)
    second = reconcile_sale_ledger.audit_database(path)

    assert first == second
    assert first["summary"] == {"eligible_sales": 1, "missing": 0, "exact": 1, "conflict": 0}
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before_hash
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT * FROM ledger_entries").fetchall() == before_rows


def test_matching_is_conservative_and_never_uses_similar_manual_entry(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        _sale(connection, 1)
        _ledger(connection, 10, None, source_type="manual")

    report = reconcile_sale_ledger.audit_database(path)

    assert report["groups"]["missing"] == [{"invoice_id": 1, "customer_id": 10, "due_total_rial": 900}]
    assert report["groups"]["exact"] == []
    assert report["groups"]["conflict"] == []


def test_conflicts_explain_field_allocation_and_orphan_source_mismatches(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        _sale(connection, 2)
        _ledger(connection, 20, 2, person_id=99, remaining=500)
        _ledger(connection, 30, 404)

    report = reconcile_sale_ledger.audit_database(path)

    assert report["summary"] == {"eligible_sales": 1, "missing": 0, "exact": 0, "conflict": 2}
    reasons = [reason["code"] for reason in report["groups"]["conflict"][0]["reasons"]]
    assert reasons == ["person_id_mismatch", "allocation_mismatch"]
    assert report["groups"]["conflict"][1] == {
        "invoice_id": 404,
        "ledger_entry_ids": [30],
        "reasons": [{"code": "sale_source_invoice_missing"}],
    }


def test_cli_exit_codes_and_json_are_machine_readable(tmp_path: Path, capsys) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        _sale(connection, 1)
    url = f"sqlite:///{path.as_posix()}"

    assert reconcile_sale_ledger.main(["--database-url", url]) == reconcile_sale_ledger.EXIT_RECONCILIATION_REQUIRED
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "dry-run"
    assert payload["read_only"] is True
    assert str(path) not in json.dumps(payload)

    with sqlite3.connect(path) as connection:
        _ledger(connection, 1, 1)
    assert reconcile_sale_ledger.main(["--database-url", url]) == reconcile_sale_ledger.EXIT_CLEAN
    clean_payload = json.loads(capsys.readouterr().out)
    assert clean_payload["summary"]["exact"] == 1


def test_cli_operational_error_is_sanitized(tmp_path: Path, capsys) -> None:
    secret_path = tmp_path / "customer-secret.db"
    result = reconcile_sale_ledger.main(["--database-url", f"sqlite:///{secret_path.as_posix()}"])

    assert result == reconcile_sale_ledger.EXIT_OPERATIONAL_ERROR
    output = capsys.readouterr().out
    assert "customer-secret" not in output
    assert json.loads(output) == {"schema_version": 1, "error": "FileNotFoundError"}


def test_valid_canceled_sale_entry_is_not_reported_as_conflict(tmp_path: Path) -> None:
    path = _database(tmp_path)
    with sqlite3.connect(path) as connection:
        _sale(connection, 1)
        connection.execute(
            "UPDATE sale_invoices SET status = 'canceled', is_active = 0 WHERE id = 1"
        )
        _ledger(connection, 1, 1, remaining=0)
        connection.execute(
            "UPDATE ledger_entries SET status = 'canceled', is_active = 0 WHERE id = 1"
        )

    report = reconcile_sale_ledger.audit_database(path)

    assert report["summary"] == {"eligible_sales": 0, "missing": 0, "exact": 0, "conflict": 0}


def test_read_only_uri_handles_reserved_path_characters(tmp_path: Path) -> None:
    path = _database(tmp_path, "legacy data #1.db")
    with sqlite3.connect(path) as connection:
        _sale(connection, 1)
        _ledger(connection, 1, 1)

    report = reconcile_sale_ledger.audit_database(path)

    assert report["summary"]["exact"] == 1
