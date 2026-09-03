from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.catalog import Category, Product, ProductVariant, Unit
from app.models.purchases import InventoryItem
from app.models.user import User

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        user = User(
            username="admin",
            full_name="System Admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True,
        )
        unit = Unit(name="Kilogram", symbol="kg")
        category = Category(name="Rice")
        product = Product(name="Rice", category=category)
        variant = ProductVariant(
            product=product,
            unit=unit,
            name="Tarem Rice",
            retail_price_rial=1_250_000,
        )
        db.add_all([user, unit, category, product, variant])
        db.commit()
        yield db

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def sale_payload() -> dict:
    return {
        "customer_name": "Customer One",
        "jalali_date": "1405/06/10",
        "local_time": "09:30",
        "discount_amount_rial": 100_000,
        "items": [
            {
                "variant_id": 1,
                "quantity": "2",
                "unit_price_rial": 1_500_000,
                "discount_amount_rial": 0,
                "estimated_cost_rial": 2_000_000,
            }
        ],
        "payments": [
            {"method": "cash", "amount_rial": 1_400_000},
            {"method": "credit", "amount_rial": 1_500_000, "due_jalali_date": "1405/06/20"},
        ],
    }


def purchase_payload() -> dict:
    return {
        "supplier_name": "Supplier One",
        "jalali_date": "1405/06/01",
        "local_time": "10:15",
        "discount_amount_rial": 0,
        "extra_cost_rial": 0,
        "paid_total_rial": 0,
        "items": [{"variant_id": 1, "quantity": "10", "unit_cost_rial": 900_000}],
    }


def create_person(
    client: TestClient,
    auth_headers: dict[str, str],
    name: str,
    person_type: str = "customer",
) -> dict:
    response = client.post(
        "/api/v1/persons",
        json={"name": name, "phone": "09120000000", "person_type": person_type},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


def seed_sale_inventory(db_session: Session) -> None:
    db_session.add(InventoryItem(variant_id=1, quantity_on_hand=Decimal("100"), weighted_average_cost_rial=1_000_000))
    db_session.commit()


def test_sales_summary_and_profit_loss_reports(client: TestClient, db_session: Session, auth_headers: dict[str, str]) -> None:
    seed_sale_inventory(db_session)
    created = client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers)
    assert created.status_code == 201

    summary = client.get(
        "/api/v1/reports/sales-summary?from_jalali=1405/06/01&to_jalali=1405/06/30",
        headers=auth_headers,
    )
    profit = client.get(
        "/api/v1/reports/profit-loss?from_jalali=1405/06/01&to_jalali=1405/06/30",
        headers=auth_headers,
    )

    assert summary.status_code == 200
    assert summary.json()["invoice_count"] == 1
    assert summary.json()["registered_sales_rial"] == 2_900_000
    assert summary.json()["received_rial"] == 1_400_000
    assert summary.json()["pending_rial"] == 1_500_000
    assert summary.json()["average_invoice_rial"] == 2_900_000
    assert profit.status_code == 200
    assert profit.json()["sales_rial"] == 2_900_000
    assert profit.json()["estimated_cost_rial"] == 2_000_000
    assert profit.json()["gross_profit_rial"] == 900_000
    assert profit.json()["gross_margin_percent"] == 31.03


def test_inventory_report_flags_reorder_and_values_stock(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    response = client.post("/api/v1/purchase-invoices", json=purchase_payload(), headers=auth_headers)
    assert response.status_code == 201
    inventory = db_session.query(InventoryItem).filter(InventoryItem.variant_id == 1).one()
    inventory.reorder_level = Decimal("10")
    db_session.commit()

    report = client.get("/api/v1/reports/inventory", headers=auth_headers)

    assert report.status_code == 200
    data = report.json()
    assert data["item_count"] == 1
    assert data["total_value_rial"] == 9_000_000
    assert data["low_stock_count"] == 1
    assert data["items"][0]["weighted_average_cost_rial"] == 900_000
    assert Decimal(data["items"][0]["quantity_on_hand"]) == Decimal("10.000")
    assert data["items"][0]["needs_reorder"] is True


def test_cashflow_and_customer_debt_reports(client: TestClient, db_session: Session, auth_headers: dict[str, str]) -> None:
    seed_sale_inventory(db_session)
    customer = create_person(client, auth_headers, "Customer One")
    supplier = create_person(client, auth_headers, "Supplier One", "supplier")
    client.post("/api/v1/sales", json=sale_payload(), headers=auth_headers)
    ledger = client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": customer["id"],
            "entry_type": "debit",
            "amount_rial": 2_000_000,
            "jalali_date": "1405/06/05",
            "local_time": "10:00",
            "description": "Opening debt",
        },
        headers=auth_headers,
    )
    assert ledger.status_code == 201
    payable = client.post(
        "/api/v1/ledger/manual-entry",
        json={
            "person_id": supplier["id"],
            "entry_type": "credit",
            "amount_rial": 750_000,
            "jalali_date": "1405/06/06",
            "local_time": "10:30",
            "description": "Supplier payable",
        },
        headers=auth_headers,
    )
    assert payable.status_code == 201
    client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "received",
            "person_id": customer["id"],
            "bank_name": "Melli",
            "cheque_number": "111",
            "amount_rial": 3_000_000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/20",
            "local_time": "10:00",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/cheques",
        json={
            "cheque_type": "paid",
            "person_id": supplier["id"],
            "bank_name": "Saderat",
            "cheque_number": "222",
            "amount_rial": 1_000_000,
            "issue_jalali_date": "1405/06/01",
            "due_jalali_date": "1405/06/20",
            "local_time": "10:00",
        },
        headers=auth_headers,
    )

    cashflow = client.get("/api/v1/reports/cashflow?jalali_date_to=1405/06/30", headers=auth_headers)
    debts = client.get("/api/v1/reports/customer-debts", headers=auth_headers)

    assert cashflow.status_code == 200
    assert cashflow.json()["pending_sales_payments_rial"] == 1_500_000
    assert cashflow.json()["unallocated_sales_due_rial"] == 0
    assert cashflow.json()["total_sales_receivables_rial"] == 1_500_000
    assert cashflow.json()["open_customer_receivables_rial"] == 2_000_000
    assert cashflow.json()["open_supplier_payables_rial"] == 750_000
    assert cashflow.json()["open_ledger_rial"] == 1_250_000
    assert cashflow.json()["pending_received_cheques_rial"] == 3_000_000
    assert cashflow.json()["pending_paid_cheques_rial"] == 1_000_000
    assert cashflow.json()["net_expected_rial"] == 4_750_000
    assert debts.status_code == 200
    assert debts.json()["total_remaining_rial"] == 2_000_000
    assert debts.json()["people"][0]["person_name"] == "Customer One"


def test_customer_debt_nets_credit_per_person_and_clamps_at_zero(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    debtor = create_person(client, auth_headers, "Net Debtor")
    creditor = create_person(client, auth_headers, "Net Creditor")
    for person_id, entry_type, amount in [
        (debtor["id"], "debit", 2_000_000),
        (debtor["id"], "credit", 600_000),
        (creditor["id"], "debit", 200_000),
        (creditor["id"], "credit", 500_000),
    ]:
        response = client.post(
            "/api/v1/ledger/manual-entry",
            json={
                "person_id": person_id,
                "entry_type": entry_type,
                "amount_rial": amount,
                "jalali_date": "1405/06/05",
                "local_time": "10:00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    report = client.get("/api/v1/reports/customer-debts", headers=auth_headers)

    assert report.status_code == 200
    assert report.json()["total_remaining_rial"] == 1_400_000
    assert report.json()["people"] == [
        {"person_id": debtor["id"], "person_name": "Net Debtor", "remaining_rial": 1_400_000}
    ]


def test_cashflow_keeps_unallocated_invoice_due_visible(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    seed_sale_inventory(db_session)
    payload = sale_payload()
    payload["payments"] = [{"method": "cash", "amount_rial": 1_000_000}]
    created = client.post("/api/v1/sales", json=payload, headers=auth_headers)
    assert created.status_code == 201
    assert created.json()["due_total_rial"] == 1_900_000

    report = client.get("/api/v1/reports/cashflow?jalali_date_to=1405/06/30", headers=auth_headers)

    assert report.status_code == 200
    assert report.json()["pending_sales_payments_rial"] == 0
    assert report.json()["unallocated_sales_due_rial"] == 1_900_000
    assert report.json()["total_sales_receivables_rial"] == 1_900_000
    assert report.json()["net_expected_rial"] == 1_900_000


def test_undated_pending_payment_remains_unallocated_receivable(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
) -> None:
    seed_sale_inventory(db_session)
    payload = sale_payload()
    payload["payments"] = [{"method": "credit", "amount_rial": 1_000_000, "status": "pending"}]
    created = client.post("/api/v1/sales", json=payload, headers=auth_headers)
    assert created.status_code == 201

    report = client.get("/api/v1/reports/cashflow?jalali_date_to=1405/06/30", headers=auth_headers)

    assert report.status_code == 200
    assert report.json()["pending_sales_payments_rial"] == 0
    assert report.json()["unallocated_sales_due_rial"] == 2_900_000


def test_both_person_participates_in_receivable_and_payable_components(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    receivable = create_person(client, auth_headers, "Both Receivable", "both")
    payable = create_person(client, auth_headers, "Both Payable", "both")
    for person_id, entry_type, amount in [
        (receivable["id"], "debit", 900_000),
        (payable["id"], "credit", 400_000),
    ]:
        response = client.post(
            "/api/v1/ledger/manual-entry",
            json={
                "person_id": person_id,
                "entry_type": entry_type,
                "amount_rial": amount,
                "jalali_date": "1405/06/05",
                "local_time": "10:00",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

    cashflow = client.get("/api/v1/reports/cashflow?jalali_date_to=1405/06/30", headers=auth_headers)
    debts = client.get("/api/v1/reports/customer-debts", headers=auth_headers)

    assert cashflow.json()["open_customer_receivables_rial"] == 900_000
    assert cashflow.json()["open_supplier_payables_rial"] == 400_000
    assert debts.json()["total_remaining_rial"] == 900_000


def test_report_date_validation_rejects_gregorian_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/reports/sales-summary?from_jalali=2026-08-24&to_jalali=1405/06/30",
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_report_date_validation_rejects_reversed_range(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/reports/profit-loss?from_jalali=1405/06/30&to_jalali=1405/06/01",
        headers=auth_headers,
    )

    assert response.status_code == 422
