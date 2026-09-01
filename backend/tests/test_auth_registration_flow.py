import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import product
from app.core.roles import UserRole
from app.database.session import get_db
from app.main import app
from app.models.subscription import Subscription
from app.models.user import User


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine)
    Subscription.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_register_login_me_and_subscription_flow(auth_client, monkeypatch):
    client, session_factory = auth_client
    credentials = {
        "username": "new_customer",
        "email": "new.customer@example.com",
        "password": "correct-horse-battery-staple",
    }

    register_response = client.post("/api/v1/auth/register", json=credentials)

    assert register_response.status_code == 200
    user_id = register_response.json()["id"]

    with session_factory() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.hashed_password != credentials["password"]
        assert user.hashed_password.startswith("$argon2")
        assert user.role == UserRole.VIEWER
        assert user.is_active is True

        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).one()
        assert subscription.plan == "free"
        assert subscription.active is True

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"

    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["id"] == user_id
    assert me_response.json()["email"] == credentials["email"]
    assert me_response.json()["role"] == "viewer"

    monkeypatch.setattr(
        product.service,
        "get_today_predictions",
        lambda **_: {
            "sport": None,
            "slate_date": "2026-09-01",
            "count": 0,
            "predictions": [],
        },
    )
    product_response = client.get(
        "/api/v1/product/predictions/today",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert product_response.status_code == 200
    assert product_response.json() == {
        "sport": None,
        "slate_date": "2026-09-01",
        "count": 0,
        "predictions": [],
    }

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]

    wrong_password_response = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": "wrong-password"},
    )
    assert wrong_password_response.status_code == 401
    assert wrong_password_response.json() == {"detail": "Invalid credentials"}

    duplicate_email_response = client.post(
        "/api/v1/auth/register",
        json={**credentials, "username": "different_username"},
    )
    assert duplicate_email_response.status_code == 400
    assert duplicate_email_response.json() == {"detail": "Email already registered"}

    duplicate_username_response = client.post(
        "/api/v1/auth/register",
        json={
            **credentials,
            "email": "different.customer@example.com",
        },
    )
    assert duplicate_username_response.status_code == 400
    assert duplicate_username_response.json() == {"detail": "Username already registered"}


@pytest.mark.parametrize(
    "stored_hash",
    ["not-a-supported-password-hash", "$2b$12$malformed"],
)
def test_login_rejects_invalid_hash_without_internal_error(auth_client, stored_hash):
    client, session_factory = auth_client
    with session_factory() as db:
        db.add(
            User(
                username="invalid_hash_user",
                email="invalid.hash@example.com",
                hashed_password=stored_hash,
                role=UserRole.VIEWER,
                is_active=True,
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "invalid.hash@example.com", "password": "irrelevant-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_login_lockout_remains_enforced(auth_client):
    client, _ = auth_client
    credentials = {
        "username": "lockout_customer",
        "email": "lockout.customer@example.com",
        "password": "correct-lockout-password",
    }
    assert client.post("/api/v1/auth/register", json=credentials).status_code == 200

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": credentials["email"], "password": "wrong-password"},
        )
        assert response.status_code == 401

    locked_response = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    assert locked_response.status_code == 401
    assert locked_response.json() == {"detail": "Invalid credentials"}


def test_login_accepts_verified_legacy_bcrypt_hash(auth_client):
    client, session_factory = auth_client
    password = "legacy-customer-password"
    legacy_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with session_factory() as db:
        db.add(
            User(
                username="legacy_customer",
                email="legacy.customer@example.com",
                hashed_password=legacy_hash,
                role=UserRole.VIEWER,
                is_active=True,
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "legacy.customer@example.com", "password": password},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]