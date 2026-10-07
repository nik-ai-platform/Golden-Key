"""Opt-in tests restricted to a disposable loopback PostgreSQL fixture."""

import importlib.util
import multiprocessing
import os
import time
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import DefaultClause, MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth.hashing import HashingService
from app.auth.jwt import JWTError, JWTService
from app.auth.service import AuthenticationService
from app.auth.session_store import SessionStore
from app.core.roles import UserRole
from app.models.auth_state import AUTH_STATE_MODELS, EmailVerificationToken, RefreshSession
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken


def _password_race_worker(url, schema, operation, token, barrier, queue):
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with Session(engine) as db:
            auth = AuthenticationService()
            barrier.wait(timeout=30)
            if operation == "reset":
                queue.put(("reset", auth.reset_password(db, token, "reset-race-password")))
            else:
                try:
                    result = auth.refresh(db, token)
                    queue.put(("refresh", (result.access_token, result.refresh_token)))
                except JWTError:
                    queue.put(("refresh", None))
    except Exception as exc:
        queue.put(("error", type(exc).__name__))
    finally:
        engine.dispose()


def _worker(url, schema, operation, barrier, queue):
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with Session(engine) as db:
            barrier.wait(timeout=30)
            store = SessionStore(db)
            if operation == "rotate":
                result = store.rotate_refresh_session(
                    "shared-old", str(uuid4()), 1, int(time.time()) + 600
                )
                db.commit()
            elif operation == "resend":
                delivery = AuthenticationService().request_email_verification(db, "synthetic@example.com")
                result = delivery.token if delivery is not None else None
            else:
                result = store.register_failed_login("synthetic@example.com", 15, 5)
            queue.put(("ok", result))
    except Exception as exc:
        queue.put(("error", type(exc).__name__))
    finally:
        engine.dispose()


@pytest.fixture
def pg_auth():
    raw_url = os.environ.get("AUTH_TEST_POSTGRES_URL")
    if not raw_url:
        pytest.skip("AUTH_TEST_POSTGRES_URL must name a disposable loopback PostgreSQL fixture")
    url = make_url(raw_url)
    if url.host not in {"127.0.0.1", "localhost", "::1"} or url.database != "launch_validation":
        pytest.fail("Auth PostgreSQL tests require loopback disposable launch_validation database")
    schema = f"auth_validation_{uuid4().hex}"
    admin = create_engine(raw_url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(raw_url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        # User's legacy ORM enum stores names but its DDL default uses a value.
        # Only adapt the isolated fixture; the auth migration never alters users.
        user_table = User.__table__.to_metadata(MetaData())
        user_table.c.role.server_default = DefaultClause("VIEWER")
        user_table.create(engine)
        path = Path(__file__).parents[1] / "migrations" / "versions" / "f8a1d3c6b920_add_durable_auth_state.py"
        spec = importlib.util.spec_from_file_location("auth_pg_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with engine.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            for model in AUTH_STATE_MODELS:
                assert connection.execute(select(model.__table__)).first() is None
        with Session(engine) as db:
            db.add(User(
                username="synthetic", email="synthetic@example.com",
                hashed_password=HashingService().hash_password("synthetic-password"),
                role=UserRole.VIEWER, is_active=True,
            ))
            db.commit()
        yield engine, raw_url, schema, migration
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def _run_workers(url, schema, operation, count):
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(count)
    queue = context.Queue()
    processes = [
        context.Process(target=_worker, args=(url, schema, operation, barrier, queue))
        for _ in range(count)
    ]
    try:
        for process in processes:
            process.start()
        results = [queue.get(timeout=60) for _ in processes]
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        assert all(status == "ok" for status, _ in results), results
        return [result for _, result in results]
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)
        queue.close()
        queue.join_thread()


def test_postgres_multiprocess_refresh_rotation_and_lockout(pg_auth):
    engine, url, schema, _ = pg_auth
    with Session(engine) as db:
        SessionStore(db).create_refresh_session("shared-old", 1, int(time.time()) + 600)
        db.commit()
    assert sorted(_run_workers(url, schema, "rotate", 2)) == [False, True]
    with Session(engine) as db:
        assert len(db.scalars(select(RefreshSession)).all()) == 2
        assert not SessionStore(db).is_refresh_session_active("shared-old")
    assert sorted(attempts for attempts, _ in _run_workers(url, schema, "failure", 5)) == [1, 2, 3, 4, 5]
    with Session(engine) as db:
        assert SessionStore(db).is_locked("synthetic@example.com")
        assert SessionStore(db).register_failed_login("synthetic@example.com", 15, 5) == (5, True)


def test_postgres_recipient_cooldown_survives_process_replacement_and_concurrent_resends(pg_auth):
    engine, url, schema, _ = pg_auth
    results = _run_workers(url, schema, "resend", 5)
    tokens = [token for token in results if token is not None]
    assert len(tokens) == 1
    first = tokens[0]
    assert _run_workers(url, schema, "resend", 2) == [None, None]
    with Session(engine) as db:
        row = db.scalars(select(EmailVerificationToken)).one()
        assert row.token_digest == SessionStore.digest(first)
        assert row.issued_at > int(time.time()) - 60
        row.issued_at = int(time.time()) - 60
        db.commit()
    later = [token for token in _run_workers(url, schema, "resend", 2) if token is not None]
    assert len(later) == 1
    with Session(engine) as db:
        auth = AuthenticationService()
        assert auth.request_email_verification(db, "synthetic@example.com") is None
        assert not auth.verify_email(db, first)
        assert auth.verify_email(db, later[0])
    assert _run_workers(url, schema, "resend", 2) == [None, None]


def test_postgres_fresh_instances_verification_cleanup_and_downgrade(pg_auth):
    engine, _, _, migration = pg_auth
    with Session(engine) as db:
        auth = AuthenticationService()
        legacy, _, _ = JWTService().create_access_token({"sub": "synthetic@example.com", "uid": 1})
        with pytest.raises(JWTError, match="revoked"):
            auth.current_user(db, legacy)
        tokens = auth.login(db, "synthetic@example.com", "synthetic-password")
        delivery = auth.request_email_verification(db, "synthetic@example.com")
    with Session(engine) as db:
        auth = AuthenticationService()
        assert auth.verify_email(db, delivery.token)
        rotated = auth.refresh(db, tokens.refresh_token)
    with Session(engine) as db:
        auth = AuthenticationService()
        assert auth.current_user(db, rotated.access_token).email_verified
        assert not auth.verify_email(db, delivery.token)
        auth.revoke_session(db, rotated.access_token, rotated.refresh_token)
    with Session(engine) as db:
        with pytest.raises(JWTError, match="revoked"):
            AuthenticationService().current_user(db, rotated.access_token)
        counts = SessionStore(db).cleanup_expired(now=int(time.time()) + 10_000_000)
        assert counts["auth_access_sessions"] == 2
        assert counts["auth_refresh_sessions"] == 2
        assert SessionStore(db).is_email_verified(1, "synthetic@example.com")
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
        assert inspect(connection).get_table_names() == ["users"]


def test_postgres_concurrent_refresh_and_reset_cannot_resurrect_sessions(pg_auth):
    engine, url, schema, _ = pg_auth
    PasswordResetToken.__table__.create(engine)
    with Session(engine) as db:
        auth = AuthenticationService()
        initial = auth.login(db, "synthetic@example.com", "synthetic-password")
        reset = auth.request_password_reset(db, "synthetic@example.com")
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    queue = context.Queue()
    processes = [
        context.Process(target=_password_race_worker, args=(
            url, schema, operation, token, barrier, queue,
        ))
        for operation, token in (("refresh", initial.refresh_token), ("reset", reset.token))
    ]
    try:
        for process in processes:
            process.start()
        results = dict(queue.get(timeout=60) for _ in processes)
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        assert "error" not in results, results
        assert results["reset"] is True
        with Session(engine) as db:
            auth = AuthenticationService()
            with pytest.raises(JWTError, match="revoked"):
                auth.current_user(db, initial.access_token)
            with pytest.raises(JWTError, match="revoked"):
                auth.refresh(db, initial.refresh_token)
            if results["refresh"] is not None:
                access_token, refresh_token = results["refresh"]
                with pytest.raises(JWTError, match="revoked"):
                    auth.current_user(db, access_token)
                with pytest.raises(JWTError, match="revoked"):
                    auth.refresh(db, refresh_token)
            assert auth.login(db, "synthetic@example.com", "reset-race-password")
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)
        queue.close()
        queue.join_thread()
