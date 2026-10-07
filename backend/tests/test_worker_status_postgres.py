from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import DBAPIError

from app.database.worker_ownership import WorkerOwnership, ownership_key
from app.services.worker_status_service import WorkerStatusService
from app.services.worker_telemetry_service import WorkerTelemetryService
from test_worker_observability_postgres import postgres, migrated, scoped_database
from test_worker_telemetry import TABLES, cycle, finish, register


def test_status_observes_real_ownership_in_read_only_snapshot_without_mutating(migrated):
    database, _, _ = migrated
    service = WorkerTelemetryService(database)
    now = datetime.now(UTC)
    instance = register(service, at=now)
    identifier, sources = cycle(service, instance, at=now)
    finish(service, identifier, sources, at=now)
    ownership = WorkerOwnership(database)
    lease = ownership.acquire(instance)
    assert lease is not None
    observed = []
    statements = []
    def isolation(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
        if statement.startswith("SET TRANSACTION"):
            observed.append((
                connection.exec_driver_sql("SHOW transaction_read_only").scalar(),
                connection.exec_driver_sql("SHOW transaction_isolation").scalar(),
            ))
    with database.transaction() as session:
        before = [session.execute(select(table)).mappings().all() for table in TABLES]
    event.listen(database.engine, "after_cursor_execute", isolation)
    try:
        response = WorkerStatusService(database).read(at=now)
        assert response.workers[1].health == "healthy"
        assert response.workers[1].latest_instance.ownership_held is True
        assert observed == [("on", "repeatable read")]
        assert all(statement.startswith(("SET", "SELECT", "SHOW")) for statement in statements)
        assert not any("pg_try_advisory" in statement or "pg_advisory_unlock" in statement for statement in statements)
        lease.check()
    finally:
        event.remove(database.engine, "after_cursor_execute", isolation)
        lease.close()
        ownership.dispose()
    with database.transaction() as session:
        assert [session.execute(select(table)).mappings().all() for table in TABLES] == before
    assert WorkerStatusService(database).read(at=now).workers[1].latest_instance.ownership_held is False


def test_postgres_rejects_mutation_in_status_transaction(migrated):
    database, _, _ = migrated
    with pytest.raises(DBAPIError):
        with database.engine.begin() as connection:
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            connection.execute(text("DELETE FROM worker_instances"))


def test_transaction_only_recovery_lock_cannot_prove_retained_worker_ownership(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    now = datetime.now(UTC)
    instance = register(service, at=now - timedelta(hours=1))
    identifier, sources = cycle(service, instance, at=now)
    finish(service, identifier, sources, at=now)
    recovery = scoped_database(url, schema)
    try:
        with recovery.transaction() as session:
            assert session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": ownership_key(instance)})
            worker = WorkerStatusService(database).read(at=now).workers[1]
            assert worker.latest_instance.ownership_held is None
            assert worker.health == "unknown"
        assert WorkerStatusService(database).read(at=now).workers[1].latest_instance.ownership_held is False
    finally:
        recovery.dispose()


def test_session_ownership_is_unknown_during_a_holder_transaction(migrated):
    database, _, _ = migrated
    service = WorkerTelemetryService(database)
    now = datetime.now(UTC)
    instance = register(service, at=now - timedelta(hours=1))
    identifier, sources = cycle(service, instance, at=now)
    finish(service, identifier, sources, at=now)
    ownership = WorkerOwnership(database)
    lease = ownership.acquire(instance)
    assert lease is not None
    try:
        lease.connection.execute(text("SELECT 1"))
        worker = WorkerStatusService(database).read(at=now).workers[1]
        assert worker.latest_instance.ownership_held is None
        assert worker.health == "unknown"
        lease.connection.commit()
        assert WorkerStatusService(database).read(at=now).workers[1].health == "healthy"
    finally:
        lease.close()
        ownership.dispose()
