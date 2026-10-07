import importlib.util
import io
import json
import sys
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import router
from app.auth.dependencies import get_auth_service
from app.auth.hashing import HashingService
from app.auth.jwt import JWTError, JWTService
from app.auth.service import AuthenticationService
from app.auth.session_store import SessionStore
from app.core.roles import UserRole
from app.database.session import get_db
from app.models.auth_state import (
    AUTH_STATE_MODELS, EXPIRING_AUTH_MODELS, AccessSession, EmailVerificationToken, LoginFailure, RefreshSession, RevokedToken,
)
from app.models.user import User


class FakeMail:
    def __init__(self):
        self.deliveries = []

    def send_email_verification(self, recipient, token):
        self.deliveries.append((recipient, token))


@pytest.fixture
def auth_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    User.__table__.create(engine)
    for model in AUTH_STATE_MODELS:
        model.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(User(
            username="synthetic", email="synthetic@example.com",
            hashed_password=HashingService().hash_password("synthetic-password"),
            role=UserRole.VIEWER, is_active=True,
        ))
        db.commit()
    yield factory
    engine.dispose()


def test_fresh_instances_preserve_login_refresh_revocation(auth_db):
    with auth_db() as db:
        tokens = AuthenticationService().login(db, "synthetic@example.com", "synthetic-password")
    with auth_db() as db:
        assert AuthenticationService().current_user(db, tokens.access_token).id == 1
        rotated = AuthenticationService().refresh(db, tokens.refresh_token)
    with auth_db() as db:
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().refresh(db, tokens.refresh_token)
        AuthenticationService().revoke_session(db, rotated.access_token, rotated.refresh_token)
    with auth_db() as db:
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().current_user(db, rotated.access_token)
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().refresh(db, rotated.refresh_token)
        rows = db.scalars(select(RefreshSession)).all()
        assert len(rows) == 2
        assert all(len(row.token_digest) == 64 for row in rows)
        assert tokens.refresh_token not in repr([row.token_digest for row in rows])


def test_unpersisted_legacy_refresh_is_invalid(auth_db):
    token, _, _ = JWTService().create_refresh_token(
        {"sub": "synthetic@example.com", "uid": 1}, expires_delta=timedelta(minutes=10)
    )
    with auth_db() as db:
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().refresh(db, token)


def test_unpersisted_pre_cutover_access_is_invalid_in_fresh_instance(auth_db):
    token, _, _ = JWTService().create_access_token({"sub": "synthetic@example.com", "uid": 1})
    with auth_db() as db:
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().current_user(db, token)


@pytest.mark.parametrize("action", ["change", "reset"])
def test_password_update_invalidates_existing_access_and_refresh(auth_db, action):
    from app.models.password_reset_token import PasswordResetToken

    with auth_db() as db:
        PasswordResetToken.__table__.create(db.get_bind())
        auth = AuthenticationService()
        tokens = auth.login(db, "synthetic@example.com", "synthetic-password")
        if action == "reset":
            delivery = auth.request_password_reset(db, "synthetic@example.com")
            assert auth.reset_password(db, delivery.token, "new-synthetic-password")
        else:
            assert auth.change_password(db, db.get(User, 1), "synthetic-password", "new-synthetic-password")
    with auth_db() as db:
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().current_user(db, tokens.access_token)
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().refresh(db, tokens.refresh_token)
        assert AuthenticationService().login(db, "synthetic@example.com", "new-synthetic-password")


def test_rotation_is_single_winner_and_rollback_restores_old_token(auth_db):
    expiry = int(time.time()) + 1000
    with auth_db() as db:
        SessionStore(db).create_refresh_session("old", 1, expiry)
        db.commit()
    with auth_db() as first, auth_db() as second:
        assert SessionStore(first).is_refresh_session_active("old")
        assert SessionStore(second).is_refresh_session_active("old")
        assert SessionStore(first).rotate_refresh_session("old", "aborted", 1, expiry)
        first.rollback()
        assert SessionStore(first).is_refresh_session_active("old")
        assert SessionStore(first).rotate_refresh_session("old", "winner", 1, expiry)
        first.commit()
        assert not SessionStore(second).rotate_refresh_session("old", "loser", 1, expiry)
        second.rollback()
        assert not SessionStore(second).is_refresh_session_active("loser")


def test_lockout_persists_and_expiry_resets_attempts(auth_db, monkeypatch):
    now = int(time.time())
    monkeypatch.setattr("app.auth.session_store.time.time", lambda: now)
    for attempt in range(1, 6):
        with auth_db() as db:
            assert SessionStore(db).register_failed_login("synthetic@example.com", 15, 5) == (attempt, attempt >= 5)
    with auth_db() as db:
        store = SessionStore(db)
        assert store.is_locked("synthetic@example.com")
        assert store.register_failed_login("synthetic@example.com", 15, 5) == (5, True)
        assert db.scalars(select(LoginFailure)).one().subject_digest != "synthetic@example.com"
    monkeypatch.setattr("app.auth.session_store.time.time", lambda: now + 901)
    with auth_db() as db:
        assert not SessionStore(db).is_locked("synthetic@example.com")
        assert SessionStore(db).register_failed_login("synthetic@example.com", 15, 5) == (1, False)


def test_verification_neutral_delivery_resend_and_single_use(auth_db, monkeypatch):
    now = int(time.time())
    monkeypatch.setattr("app.auth.session_store.time.time", lambda: now)
    mail = FakeMail()
    auth_app = FastAPI()
    auth_app.include_router(router, prefix="/api/v1")

    def override_db():
        with auth_db() as db:
            yield db

    auth_app.dependency_overrides[get_db] = override_db
    auth_app.dependency_overrides[get_auth_service] = lambda: AuthenticationService(mail_sender=mail)
    with TestClient(auth_app) as client:
        known = client.post("/api/v1/auth/email-verification", json={"email": "synthetic@example.com"})
        unknown = client.post("/api/v1/auth/email-verification", json={"email": "missing@example.com"})
        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        assert len(mail.deliveries) == 1
        first_token = mail.deliveries[-1][1]
        assert first_token not in str(known.json())
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {first_token}"}).status_code == 401
        resent = client.post("/api/v1/auth/email-verification/resend", json={"email": "synthetic@example.com"})
        assert resent.json() == known.json()
        assert len(mail.deliveries) == 1
        with auth_db() as db:
            assert db.scalars(select(EmailVerificationToken)).one().token_digest == SessionStore.digest(first_token)
        now += 59
        assert client.post("/api/v1/auth/email-verification/resend", json={"email": "synthetic@example.com"}).json() == known.json()
        assert len(mail.deliveries) == 1
        now += 1
        assert client.post("/api/v1/auth/email-verification/resend", json={"email": "synthetic@example.com"}).json() == known.json()
        assert len(mail.deliveries) == 2
        token = mail.deliveries[-1][1]
        assert token != first_token
        with auth_db() as db:
            row = db.scalars(select(EmailVerificationToken)).one()
            assert row.token_digest == SessionStore.digest(token)
            assert len(row.token_digest) == 64
        assert client.post("/api/v1/auth/email-verification/confirm", json={"token": first_token}).status_code == 400
        assert client.post("/api/v1/auth/email-verification/confirm", json={"token": token}).status_code == 200
        assert client.post("/api/v1/auth/email-verification/confirm", json={"token": token}).status_code == 400
        logged_in = client.post("/api/v1/auth/login", json={
            "email": "synthetic@example.com", "password": "synthetic-password",
        })
        profile = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {logged_in.json()['access_token']}",
        })
        assert profile.status_code == 200
        assert profile.json()["email_verified"] is True
        with auth_db() as db:
            SessionStore(db).cleanup_expired()
            assert SessionStore(db).is_email_verified(1, "synthetic@example.com")
        verified = client.post("/api/v1/auth/email-verification", json={"email": "synthetic@example.com"})
        assert verified.json() == known.json()
        assert len(mail.deliveries) == 2


@pytest.mark.parametrize("email", ["registered@example.com", "Registered@example.com"])
def test_auth_registration_queues_verification_without_changing_response(auth_db, email):
    from app.models.subscription import Subscription

    with auth_db() as db:
        Subscription.__table__.create(db.get_bind())
    mail = FakeMail()
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    def override_db():
        with auth_db() as db:
            yield db

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_auth_service] = lambda: AuthenticationService(mail_sender=mail)
    credentials = {
        "username": "registered-synthetic", "email": email,
        "password": "registered-synthetic-password",
    }
    with TestClient(test_app) as client:
        response = client.post("/api/v1/auth/register", json=credentials)
        assert response.status_code == 200
        assert response.json()["email"] == email.lower()
        assert len(mail.deliveries) == 1
        recipient, token = mail.deliveries[0]
        assert recipient == email.lower()
        assert token not in str(response.json())
        with auth_db() as db:
            assert db.get(EmailVerificationToken, SessionStore.digest(token))
        neutral = client.post("/api/v1/auth/email-verification/resend", json={"email": recipient})
        assert neutral.status_code == 200
        assert len(mail.deliveries) == 1
        assert client.post("/api/v1/auth/register", json=credentials).status_code == 400
        duplicate = client.post("/api/v1/auth/register", json={
            **credentials, "username": "different-synthetic", "email": email.upper(),
        })
        assert duplicate.status_code == 400
        assert duplicate.json() == {"detail": "Email already registered"}
        assert len(mail.deliveries) == 1
        assert client.post("/api/v1/auth/email-verification/confirm", json={"token": token}).status_code == 200
        assert client.post("/api/v1/auth/login", json={
            "email": email.upper(), "password": credentials["password"],
        }).status_code == 200


def test_inactive_and_demo_verification_requests_are_neutral_no_delivery(auth_db):
    with auth_db() as db:
        db.get(User, 1).is_active = False
        db.commit()
        auth = AuthenticationService(mail_sender=FakeMail())
        assert auth.request_email_verification(db, "synthetic@example.com") is None
        assert auth.request_email_verification(db, "admin@example.com") is None
        assert db.scalars(select(EmailVerificationToken)).first() is None


def test_onboarding_registration_queues_fake_verification_mail(auth_db):
    from app.api.v1.onboarding import router as onboarding_router

    mail = FakeMail()
    test_app = FastAPI()
    test_app.include_router(onboarding_router, prefix="/api/v1")

    def override_db():
        with auth_db() as db:
            yield db

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_auth_service] = lambda: AuthenticationService(mail_sender=mail)
    with TestClient(test_app) as client:
        response = client.post("/api/v1/onboarding/register", json={
            "username": "onboarding-synthetic", "email": "onboarding@example.com",
            "password": "onboarding-synthetic-password", "accept_terms": True,
        })
        assert response.status_code == 201
        assert response.json()["next_step"] == "verify_email"
        assert mail.deliveries[0][0] == "onboarding@example.com"
        with auth_db() as db:
            assert db.get(EmailVerificationToken, SessionStore.digest(mail.deliveries[0][1]))


def test_main_app_onboarding_registration_remains_anonymous(auth_db):
    from app.main import app

    mail = FakeMail()

    def override_db():
        with auth_db() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: AuthenticationService(mail_sender=mail)
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/onboarding/register", json={
                "username": "public-onboarding", "email": "public-onboarding@example.com",
                "password": "public-onboarding-password", "accept_terms": True,
            })
        assert response.status_code == 201
        assert response.json()["next_step"] == "verify_email"
        assert len(mail.deliveries) == 1
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_verification_persists_expiry_and_address_binding(auth_db):
    with auth_db() as db:
        delivery = AuthenticationService().request_email_verification(db, "synthetic@example.com")
    with auth_db() as db:
        db.get(User, 1).email = "changed@example.com"
        db.commit()
        assert not AuthenticationService().verify_email(db, delivery.token)
        assert not SessionStore(db).is_email_verified(1, "changed@example.com")
        second = AuthenticationService().request_email_verification(db, "changed@example.com")
    with auth_db() as db:
        row = db.get(EmailVerificationToken, SessionStore.digest(second.token))
        row.expires_at = int(time.time()) - 1
        db.commit()
    with auth_db() as db:
        assert not AuthenticationService().verify_email(db, second.token)


def test_delivery_errors_are_neutral_and_do_not_log_secrets(auth_db, caplog):
    class BrokenMail:
        def send_email_verification(self, recipient, token):
            raise RuntimeError(f"secret {recipient} {token}")

    auth = AuthenticationService(mail_sender=BrokenMail())
    with auth_db() as db:
        delivery = auth.request_email_verification(db, "synthetic@example.com")
    auth.deliver_email_verification(delivery)
    assert delivery.token not in caplog.text
    assert delivery.recipient not in caplog.text
    assert "delivery failed" in caplog.text


def test_cleanup_is_bounded_expired_only_and_idempotent(auth_db):
    cutoff = int(time.time())
    with auth_db() as db:
        for number in range(3):
            db.add(RevokedToken(token_digest=str(number), expires_at=cutoff - 1))
        db.add(RevokedToken(token_digest="keep", expires_at=cutoff + 100))
        db.add(AccessSession(token_digest="expired", user_id=1, expires_at=cutoff, revoked=False))
        db.add(AccessSession(token_digest="live", user_id=1, expires_at=cutoff + 100, revoked=False))
        db.add(RefreshSession(token_digest="expired", user_id=1, expires_at=cutoff, revoked=False))
        db.add(RefreshSession(token_digest="revoked-live", user_id=1, expires_at=cutoff + 100, revoked=True))
        db.add(LoginFailure(subject_digest="expired", attempts=5, expires_at=cutoff))
        db.add(EmailVerificationToken(token_digest="expired", user_id=1, email="synthetic@example.com", expires_at=cutoff))
        db.commit()
        counts = SessionStore(db).cleanup_expired(batch_size=2, now=cutoff)
        assert counts == {
            "auth_access_sessions": 1,
            "auth_refresh_sessions": 1, "auth_revoked_tokens": 2,
            "auth_login_failures": 1, "auth_email_verification_tokens": 1,
        }
        assert SessionStore(db).cleanup_expired(batch_size=2, now=cutoff)["auth_revoked_tokens"] == 1
        assert not any(SessionStore(db).cleanup_expired(batch_size=2, now=cutoff).values())
        assert db.get(RevokedToken, "keep")
        assert db.get(RefreshSession, "revoked-live")
        assert db.get(AccessSession, "live")
        assert db.get(User, 1)
        with pytest.raises(ValueError):
            SessionStore(db).cleanup_expired(batch_size=10001)


def test_cleanup_cli_uses_explicit_bounded_batch(auth_db, monkeypatch, capsys):
    from scripts import cleanup_expired_auth

    monkeypatch.setattr(cleanup_expired_auth, "SessionLocal", auth_db)
    monkeypatch.setattr(sys, "argv", ["cleanup_expired_auth.py", "--batch-size", "2"])
    cleanup_expired_auth.main()
    assert json.loads(capsys.readouterr().out) == {
        "auth_access_sessions": 0,
        "auth_refresh_sessions": 0, "auth_revoked_tokens": 0,
        "auth_login_failures": 0, "auth_email_verification_tokens": 0,
    }
    monkeypatch.setattr(sys, "argv", ["cleanup_expired_auth.py", "--batch-size", "0"])
    with pytest.raises(SystemExit) as exc:
        cleanup_expired_auth.main()
    assert exc.value.code == 2


def test_postgres_lockout_upsert_compiles_as_atomic_statement():
    class CompileOnlySession:
        def get_bind(self):
            return SimpleNamespace(dialect=postgresql.dialect())

        def execute(self, statement):
            self.sql = str(statement.compile(dialect=postgresql.dialect()))
            return SimpleNamespace(one=lambda: (1, None))

        def commit(self):
            pass

    db = CompileOnlySession()
    assert SessionStore(db).register_failed_login("synthetic@example.com", 15, 5) == (1, False)
    assert "ON CONFLICT (subject_digest) DO UPDATE" in db.sql
    assert "auth_login_failures.attempts +" in db.sql
    assert "RETURNING" in db.sql


def test_migration_creates_empty_auth_tables_and_downgrades_only_auth():
    path = Path(__file__).parents[1] / "migrations" / "versions" / "f8a1d3c6b920_add_durable_auth_state.py"
    spec = importlib.util.spec_from_file_location("durable_auth_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "e7b4c2d9a610"
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        for model in AUTH_STATE_MODELS:
            assert connection.execute(select(model.__table__)).first() is None
            if model in EXPIRING_AUTH_MODELS:
                assert "expires_at" in {column["name"] for column in inspect(connection).get_columns(model.__tablename__)}
        migration.downgrade()
        assert inspect(connection).get_table_names() == ["users"]
    engine.dispose()
    output = io.StringIO()
    migration.op = Operations(MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    ))
    migration.upgrade()
    ddl = output.getvalue()
    assert "CREATE TABLE auth_refresh_sessions" in ddl
    assert "CREATE TABLE auth_verified_emails" in ddl
    assert "BIGINT" in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl
