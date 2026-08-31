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
from app.models.forgot_email_challenge import ForgotEmailChallenge
from app.models.password_reset_token import PasswordResetToken
from app.models.recovery_email_verification import RecoveryEmailVerification
from app.models.subscription import Subscription
from app.models.user import User


GENERIC_MESSAGE = (
    "If an account exists for that email, password reset instructions have been sent."
)


class FakeMailSender:
    def __init__(self) -> None:
        self.deliveries: list[tuple[str, str]] = []
        self.recovery_verifications: list[tuple[str, str]] = []
        self.forgot_email_deliveries: list[tuple[str, str]] = []

    def send_password_reset(self, recipient: str, token: str) -> None:
        self.deliveries.append((recipient, token))

    def send_recovery_email_verification(self, recipient: str, code: str) -> None:
        self.recovery_verifications.append((recipient, code))

    def send_forgot_email_code(self, recipient: str, code: str) -> None:
        self.forgot_email_deliveries.append((recipient, code))


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
    RecoveryEmailVerification.__table__.create(bind=engine)
    ForgotEmailChallenge.__table__.create(bind=engine)
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


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def configure_recovery_email(
    client: TestClient,
    mail_sender: FakeMailSender,
    headers: dict[str, str],
    recovery_email: str,
) -> str:
    response = client.post(
        "/api/v1/auth/recovery-email",
        json={"recovery_email": recovery_email},
        headers=headers,
    )
    assert response.status_code == 200
    return mail_sender.recovery_verifications[-1][1]


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


def test_authenticated_user_configures_and_verifies_recovery_email(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "customer@example.com", "old-password")
    headers = auth_headers(client, "customer@example.com", "old-password")

    code = configure_recovery_email(
        client, mail_sender, headers, "Secondary@Example.com"
    )
    with session_factory() as db:
        user = db.query(User).filter(User.email == "customer@example.com").one()
        challenge = db.query(RecoveryEmailVerification).one()
        assert user.recovery_email == "secondary@example.com"
        assert user.recovery_email_verified is False
        assert code not in challenge.code_digest
        assert len(challenge.code_digest) == 64

    unverified_profile = client.get("/api/v1/users/me", headers=headers)
    assert unverified_profile.status_code == 200
    assert unverified_profile.json()["recovery_email_masked"] == "s********@example.com"
    assert unverified_profile.json()["recovery_email_verified"] is False
    assert "secondary@example.com" not in unverified_profile.text

    response = client.post(
        "/api/v1/auth/recovery-email/verify",
        json={"code": code},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Recovery email verified"}
    profile = client.get("/api/v1/users/me", headers=headers).json()
    assert profile["recovery_email_masked"] == "s********@example.com"
    assert profile["recovery_email_verified"] is True
    assert "secondary@example.com" not in str(profile)


def test_synthetic_user_uses_existing_persistent_user_for_recovery(recovery_client):
    client, session_factory, mail_sender = recovery_client
    with session_factory() as db:
        persistent_admin = User(
            username="persistent-admin",
            email="admin@example.com",
            hashed_password=HashingService().hash_password("unused-password"),
            role="admin",
            is_active=True,
        )
        db.add(persistent_admin)
        db.commit()
        persistent_id = persistent_admin.id

    headers = auth_headers(client, "admin@example.com", "admin123")
    code = configure_recovery_email(
        client, mail_sender, headers, "admin-recovery@example.com"
    )

    with session_factory() as db:
        challenge = db.query(RecoveryEmailVerification).one()
        user = db.get(User, persistent_id)
        assert challenge.user_id == persistent_id
        assert challenge.user_id != 0
        assert user.recovery_email == "admin-recovery@example.com"

    unverified_profile = client.get("/api/v1/users/me", headers=headers)
    assert unverified_profile.status_code == 200
    assert unverified_profile.json()["id"] == 0
    assert unverified_profile.json()["recovery_email_masked"] == "a*************@example.com"
    assert unverified_profile.json()["recovery_email_verified"] is False
    assert "admin-recovery@example.com" not in unverified_profile.text

    response = client.post(
        "/api/v1/auth/recovery-email/verify",
        json={"code": code},
        headers=headers,
    )
    assert response.status_code == 200
    verified_profile = client.get("/api/v1/users/me", headers=headers)
    assert verified_profile.status_code == 200
    assert verified_profile.json()["id"] == 0
    assert verified_profile.json()["recovery_email_masked"] == "a*************@example.com"
    assert verified_profile.json()["recovery_email_verified"] is True
    assert "admin-recovery@example.com" not in verified_profile.text
    with session_factory() as db:
        assert db.get(User, persistent_id).recovery_email_verified is True


def test_synthetic_user_without_persistent_row_fails_cleanly(recovery_client):
    client, session_factory, mail_sender = recovery_client
    headers = auth_headers(client, "admin@example.com", "admin123")

    profile = client.get("/api/v1/users/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == 0
    assert profile.json()["recovery_email_masked"] is None
    assert profile.json()["recovery_email_verified"] is False

    response = client.post(
        "/api/v1/auth/recovery-email",
        json={"recovery_email": "admin-recovery@example.com"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unable to configure recovery email"}
    assert mail_sender.recovery_verifications == []
    with session_factory() as db:
        assert db.query(User).count() == 0
        assert db.query(RecoveryEmailVerification).count() == 0


def test_recovery_email_rejects_primary_and_change_resets_verification(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "customer@example.com", "old-password")
    headers = auth_headers(client, "customer@example.com", "old-password")

    same = client.post(
        "/api/v1/auth/recovery-email",
        json={"recovery_email": "CUSTOMER@example.com"},
        headers=headers,
    )
    assert same.status_code == 400

    code = configure_recovery_email(client, mail_sender, headers, "first@example.com")
    assert client.post(
        "/api/v1/auth/recovery-email/verify", json={"code": code}, headers=headers
    ).status_code == 200
    configure_recovery_email(client, mail_sender, headers, "second@example.com")
    with session_factory() as db:
        user = db.query(User).filter(User.email == "customer@example.com").one()
        assert user.recovery_email == "second@example.com"
        assert user.recovery_email_verified is False


def test_recovery_email_code_expiry_replay_and_wrong_code(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "customer@example.com", "old-password")
    headers = auth_headers(client, "customer@example.com", "old-password")

    code = configure_recovery_email(client, mail_sender, headers, "secondary@example.com")
    assert client.post(
        "/api/v1/auth/recovery-email/verify", json={"code": "000000"}, headers=headers
    ).status_code == 400
    assert client.post(
        "/api/v1/auth/recovery-email/verify", json={"code": code}, headers=headers
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/recovery-email/verify", json={"code": code}, headers=headers
    ).status_code == 400

    configure_recovery_email(client, mail_sender, headers, "new@example.com")
    with session_factory() as db:
        challenge = (
            db.query(RecoveryEmailVerification)
            .filter(RecoveryEmailVerification.used_at.is_(None))
            .one()
        )
        challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.post(
        "/api/v1/auth/recovery-email/verify",
        json={"code": mail_sender.recovery_verifications[-1][1]},
        headers=headers,
    ).status_code == 400


def test_recovery_email_verification_attempts_are_bounded(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "customer@example.com", "old-password")
    headers = auth_headers(client, "customer@example.com", "old-password")
    code = configure_recovery_email(client, mail_sender, headers, "secondary@example.com")

    for wrong_code in ["000000", "000001", "000002", "000003", "000004"]:
        assert client.post(
            "/api/v1/auth/recovery-email/verify",
            json={"code": wrong_code},
            headers=headers,
        ).status_code == 400
    assert client.post(
        "/api/v1/auth/recovery-email/verify", json={"code": code}, headers=headers
    ).status_code == 400
    with session_factory() as db:
        challenge = db.query(RecoveryEmailVerification).one()
        assert challenge.failed_attempts == 5
        assert challenge.used_at is not None


def test_forgot_email_request_is_generic_for_all_addresses(recovery_client):
    client, _, mail_sender = recovery_client
    register(client, "verified", "verified@example.com", "old-password")
    register(client, "unverified", "unverified@example.com", "old-password")
    verified_headers = auth_headers(client, "verified@example.com", "old-password")
    unverified_headers = auth_headers(client, "unverified@example.com", "old-password")
    code = configure_recovery_email(
        client, mail_sender, verified_headers, "verified-recovery@example.com"
    )
    assert client.post(
        "/api/v1/auth/recovery-email/verify",
        json={"code": code},
        headers=verified_headers,
    ).status_code == 200
    configure_recovery_email(
        client, mail_sender, unverified_headers, "unverified-recovery@example.com"
    )

    responses = [
        client.post(
            "/api/v1/auth/forgot-email", json={"recovery_email": address}
        )
        for address in (
            "verified-recovery@example.com",
            "unverified-recovery@example.com",
            "unknown@example.com",
            "not-an-email",
        )
    ]
    assert all(response.status_code == 200 for response in responses)
    assert len({response.text for response in responses}) == 1
    assert responses[0].json() == {
        "message": "If a verified recovery account matches that address, a recovery code has been sent."
    }
    assert len(mail_sender.forgot_email_deliveries) == 1


def test_forgot_email_verify_returns_only_masked_email_and_cannot_replay(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "nikhill@gmail.com", "old-password")
    headers = auth_headers(client, "nikhill@gmail.com", "old-password")
    verification_code = configure_recovery_email(
        client, mail_sender, headers, "secondary@example.com"
    )
    client.post(
        "/api/v1/auth/recovery-email/verify",
        json={"code": verification_code},
        headers=headers,
    )
    client.post(
        "/api/v1/auth/forgot-email", json={"recovery_email": "secondary@example.com"}
    )
    recovery_code = mail_sender.forgot_email_deliveries[-1][1]

    response = client.post(
        "/api/v1/auth/forgot-email/verify",
        json={"recovery_email": "secondary@example.com", "code": recovery_code},
    )
    assert response.status_code == 200
    assert response.json() == {"email": "n******@gmail.com"}
    assert "nikhill@gmail.com" not in response.text
    assert client.post(
        "/api/v1/auth/forgot-email/verify",
        json={"recovery_email": "secondary@example.com", "code": recovery_code},
    ).status_code == 400
    malformed = client.post(
        "/api/v1/auth/forgot-email/verify",
        json={"recovery_email": "secondary@example.com", "code": "malformed"},
    )
    assert malformed.status_code == 400
    assert malformed.json() == {"detail": "Invalid or expired recovery code"}
    with session_factory() as db:
        challenge = db.query(ForgotEmailChallenge).one()
        assert recovery_code not in challenge.code_digest
        assert len(challenge.code_digest) == 64


def test_forgot_email_challenge_expiry_and_attempt_limit(recovery_client):
    client, session_factory, mail_sender = recovery_client
    register(client, "customer", "a@example.com", "old-password")
    headers = auth_headers(client, "a@example.com", "old-password")
    verification_code = configure_recovery_email(
        client, mail_sender, headers, "secondary@example.com"
    )
    client.post(
        "/api/v1/auth/recovery-email/verify",
        json={"code": verification_code},
        headers=headers,
    )
    client.post(
        "/api/v1/auth/forgot-email", json={"recovery_email": "secondary@example.com"}
    )
    expired_code = mail_sender.forgot_email_deliveries[-1][1]
    with session_factory() as db:
        challenge = db.query(ForgotEmailChallenge).one()
        challenge.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.post(
        "/api/v1/auth/forgot-email/verify",
        json={"recovery_email": "secondary@example.com", "code": expired_code},
    ).status_code == 400

    client.post(
        "/api/v1/auth/forgot-email", json={"recovery_email": "secondary@example.com"}
    )
    valid_code = mail_sender.forgot_email_deliveries[-1][1]
    for wrong_code in ["000000", "000001", "000002", "000003", "000004"]:
        assert client.post(
            "/api/v1/auth/forgot-email/verify",
            json={"recovery_email": "secondary@example.com", "code": wrong_code},
        ).status_code == 400
    assert client.post(
        "/api/v1/auth/forgot-email/verify",
        json={"recovery_email": "secondary@example.com", "code": valid_code},
    ).status_code == 400


@pytest.mark.parametrize(
    ("email", "masked"),
    [
        ("nikhill@gmail.com", "n******@gmail.com"),
        ("ab@example.com", "a*@example.com"),
        ("a@example.com", "a*@example.com"),
    ],
)
def test_email_masking_never_reveals_full_local_part(email, masked):
    assert AuthenticationService.mask_email(email) == masked