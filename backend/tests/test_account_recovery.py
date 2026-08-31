from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_auth_service
from app.auth.hashing import HashingService
from app.auth.service import AuthenticationService
from app.database.session import get_db
from app.main import app
from app.models.password_reset_token import PasswordResetToken
from app.models.subscription import Subscription
from app.models.user import User


GENERIC_MESSAGE = (
    "If an account exists for that email, password reset instructions have been sent."
)


class FakeMailSender:
    def __init__(self) -> None:
        self.deliveries: list[tuple[str, str]] = []

    def send_password_reset(self, recipient: str, token: str) -> None:
        self.deliveries.append((recipient, token))


@pytest.fixture
def recovery_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine)
    Subscription.__table__.create(bind=engine)
    PasswordResetToken.__table__.create(bind=engine)
    session_factory = sessionmaker(bind=engine)
    mail_sender = FakeMailSender()
    auth_service = AuthenticationService(mail_sender=mail_sender)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    with TestClient(app) as client:
        yield client, session_factory, mail_sender
    app.dependency_overrides.clear()
    engine.dispose()


def register(client: TestClient, username: str, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 200


def request_token(client: TestClient, mail_sender: FakeMailSender, email: str) -> str:
    response = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}
    return mail_sender.deliveries[-1][1]


def test_forgot_password_does_not_enumerate_accounts(recovery_client):
    client, _, mail_sender = recovery_client
    register(client, "customer", "customer@example.com", "old-password")

    existing = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "customer@example.com"},
    )
    unknown = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )

    assert existing.status_code == unknown.status_code == 200
    assert existing.json() == unknown.json() == {"message": GENERIC_MESSAGE}
    assert len(mail_sender.deliveries) == 1
    assert "token" not in existing.json()


def test_valid_token_changes_password_once_with_canonical_hash(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "customer@example.com", "old-password")
    token = request_token(client, mail_sender, "customer@example.com")

    access_attempt = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert access_attempt.status_code == 401

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "new-secure-password"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password updated"}
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "old-password"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "new-secure-password"},
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "another-password"},
    ).status_code == 400

    with session_factory() as db:
        user = db.query(User).filter(User.email == "customer@example.com").one()
        stored = db.query(PasswordResetToken).one()
        assert user.hashed_password.startswith("$argon2")
        assert HashingService().verify_password("new-secure-password", user.hashed_password)
        assert token not in stored.token_digest
        assert len(stored.token_digest) == 64
        assert stored.used_at is not None


def test_expired_malformed_and_cross_account_tokens_are_rejected(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "first", "first@example.com", "first-password")
    register(client, "second", "second@example.com", "second-password")
    first_token = request_token(client, mail_sender, "first@example.com")

    intended_account = client.post(
        "/api/v1/auth/reset-password",
        json={"token": first_token, "new_password": "replacement-password"},
    )
    assert intended_account.status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "first@example.com", "password": "replacement-password"},
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "replacement-password"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "second-password"},
    ).status_code == 200

    with session_factory() as db:
        second = db.query(User).filter(User.email == "second@example.com").one()
        assert second.role.value == "viewer"

    expired_token = request_token(client, mail_sender, "first@example.com")
    with session_factory() as db:
        stored = db.query(PasswordResetToken).filter(PasswordResetToken.used_at.is_(None)).one()
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

    assert client.post(
        "/api/v1/auth/reset-password",
        json={"token": expired_token, "new_password": "unused-password"},
    ).status_code == 400
    assert client.post(
        "/api/v1/auth/reset-password",
        json={"token": "malformed", "new_password": "unused-password"},
    ).status_code == 400


def test_demo_account_cannot_request_password_reset(recovery_client):
    client, _, mail_sender = recovery_client

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}
    assert mail_sender.deliveries == []


def test_forgot_email_is_support_based(recovery_client):
    client, _, _ = recovery_client

    response = client.post("/api/v1/auth/forgot-email")

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If you no longer remember the email associated with your Golden Key account, "
            "contact support for account recovery."
        )
    }