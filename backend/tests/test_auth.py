from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
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
        db.add(
            User(
                username="admin",
                full_name="مدیر سیستم",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
            )
        )
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


def test_login_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["is_superuser"] is True


def test_login_with_bad_password_fails(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "نام کاربری یا رمز عبور اشتباه است."


def test_me_with_token_returns_current_user(client: TestClient) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_me_without_token_fails(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def login_token(client: TestClient, password: str = "admin123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_change_password_requires_current_password_and_invalidates_old_token(client: TestClient) -> None:
    old_token = login_token(client)
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {old_token}"},
        json={
            "current_password": "admin123",
            "new_password": "new-admin-456",
            "confirm_password": "new-admin-456",
        },
    )

    assert response.status_code == 200
    assert "دوباره وارد شوید" in response.json()["message"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "new-admin-456"}).status_code == 200


def test_change_password_rejects_wrong_current_password_without_changing_it(client: TestClient) -> None:
    token = login_token(client)
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "incorrect",
            "new_password": "new-admin-456",
            "confirm_password": "new-admin-456",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "رمز عبور فعلی درست نیست."
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


@pytest.mark.parametrize(
    "new_password,confirm_password",
    [("short", "short"), ("new-admin-456", "different-456"), ("admin123", "admin123")],
)
def test_change_password_validates_new_password_policy(
    client: TestClient, new_password: str, confirm_password: str
) -> None:
    token = login_token(client)
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "admin123",
            "new_password": new_password,
            "confirm_password": confirm_password,
        },
    )

    assert response.status_code == 422


def test_change_password_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "admin123",
            "new_password": "new-admin-456",
            "confirm_password": "new-admin-456",
        },
    )
    assert response.status_code == 401
