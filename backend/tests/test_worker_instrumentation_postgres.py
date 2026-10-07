from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from sqlalchemy import select, update, text
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4

from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import WorkerCycleSource
from app.models.worker_instance import WorkerInstance
from app.database.telemetry_session import TelemetryError
from app.database.worker_ownership import WorkerOwnership, ownership_key
from app.services.worker_telemetry_service import WorkerTelemetryService
from test_worker_observability_postgres import postgres, migrated, scoped_database
from test_worker_instrumentation import (
    business_db, block_http, records, recorder,
    test_upcoming_real_business_idempotency_source_identity_and_sequence,
    test_upcoming_provider_failure_retains_unknown_counts_and_other_sources,
    test_final_real_settlement_counters_and_idempotency,
    test_final_failed_source_does_not_hide_success,
    test_telemetry_writes_only_after_business_session_close,
    test_failed_business_session_close_suppresses_storage_and_preserves_original_exception,
    test_keyboard_interrupt_preserves_exception_and_leaves_incomplete_evidence,
    test_recovery_abandons_only_stale_cycles_and_preserves_unknown_durations,
    test_telemetry_failures_do_not_change_business_calls_or_commits,
    test_original_business_exception_survives_failed_cleanup,
    test_unexpected_prediction_setup_failure_cannot_report_source_or_cycle_success,
    test_failure_during_real_business_writes_preserves_commits_and_idempotency,
    test_shadow_hook_failure_is_auxiliary_and_keeps_business_results,
    wire_upcoming,
    test_healthy_long_sport_keeps_owned_cycle_and_can_complete,
    test_full_unwind_shares_deadline_before_first_source_write,
    test_close_exception_starts_one_deadline_and_preserves_exception,
    test_ownership_failure_keeps_business_results_and_bounded_warning,
    test_normal_completion_has_no_interruption_deadline,
)


@pytest.fixture
def database(migrated):
    return migrated[0]


def test_concurrent_source_evidence_uses_storage_locking_and_monotonic_merges(database, migrated):
    telemetry = recorder(database)
    telemetry.register()
    telemetry.start_cycle()
    source = telemetry.sources[0]
    identifier = telemetry.ids[source]
    at = datetime.now(UTC)
    telemetry.service.transition_source(telemetry.cycle_id, identifier, state="running", at=at)
    barrier = Barrier(2)
    other = scoped_database(migrated[1], migrated[2])
    def update(offset):
        service = WorkerTelemetryService(database if offset == 20 else other)
        barrier.wait(timeout=5)
        return service.transition_source(
            telemetry.cycle_id, identifier, state="running", at=at,
            counters={"fetched": 5, "errors": 2}, error_code="publication_failed",
            timestamps={"last_game_processed_at": at + timedelta(seconds=offset)},
        )
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(update, (20, 10)))
            assert outcomes[0] is True and outcomes[1] in {True, False}
    finally:
        other.dispose()
    with database.transaction() as session:
        row = session.execute(
            select(WorkerCycleSource.__table__).where(WorkerCycleSource.id == identifier)
        ).mappings().one()
        assert row["fetched"] == 5 and row["errors"] == 2
        assert row["last_game_processed_at"] == at + timedelta(seconds=20)
        assert row["error_code"] == "publication_failed"
    telemetry.service.complete_cycle(
        telemetry.cycle_id, state="failed", finished_at=at + timedelta(seconds=20),
        duration_ms=0, telemetry_complete=False,
    )
    assert records(database, WorkerCycle)[0]["state"] == "failed"


def test_actual_postgres_lock_timeout_does_not_rollback_business(
    database, migrated, business_db, monkeypatch, caplog,
):
    services, fetches = wire_upcoming(monkeypatch, business_db, {})
    blocker = scoped_database(migrated[1], migrated[2])
    from app.models.worker_instance import WorkerInstance
    from app.workers import upcoming_game_worker
    try:
        with recorder(database).process() as telemetry:
            with blocker.transaction() as session:
                session.execute(
                    select(WorkerInstance.id).where(WorkerInstance.id == telemetry.instance_id).with_for_update()
                ).one()
                result = upcoming_game_worker.run_once()
                assert result["NBA"]["prediction_errors"] == 0
                assert not telemetry.enabled
        assert fetches[0].call_count == 2
        assert records(database, WorkerCycle) == []
        assert len([record for record in caplog.records if "Worker telemetry unavailable" in record.message]) == 1
    finally:
        blocker.dispose()


def make_stale(database, telemetry):
    at = datetime.now(UTC) - timedelta(days=1)
    with database.transaction() as session:
        session.execute(update(WorkerInstance).where(WorkerInstance.id == telemetry.instance_id).values(
            started_at=at, heartbeat_at=at, progress_at=at, last_cycle_started_at=at,
        ))
        session.execute(update(WorkerCycle).where(WorkerCycle.id == telemetry.cycle_id).values(started_at=at))


def test_real_ownership_is_dedicated_and_precedes_registration(database, monkeypatch):
    telemetry = recorder(database)
    register = telemetry.service.register_instance
    observations = []
    def registered(*args, **kwargs):
        assert telemetry._lease is not None
        telemetry._lease.check()
        with database.transaction() as session:
            business_pid = session.scalar(text("SELECT pg_backend_pid()"))
        owner_pid = telemetry._lease.connection.scalar(text("SELECT pg_backend_pid()"))
        telemetry._lease.connection.commit()
        assert owner_pid != business_pid
        assert telemetry.ownership.acquire(telemetry.instance_id) is None
        observations.append(True)
        return register(*args, **kwargs)
    monkeypatch.setattr(telemetry.service, "register_instance", registered)
    with telemetry.process():
        assert telemetry.enabled
    assert observations == [True]
    assert telemetry._lease is None
    probe = WorkerOwnership(database)
    lease = probe.acquire(telemetry.instance_id)
    assert lease is not None
    lease.close()
    probe.dispose()


def test_ownership_loss_releases_lock_allows_recovery_and_degrades_original(
    database, business_db, monkeypatch, caplog,
):
    from app.workers import upcoming_game_worker
    from test_worker_instrumentation import wire_upcoming, FakeOwnership
    first, second = recorder(database), recorder(database)
    first.register()
    first.start_cycle()
    make_stale(database, first)
    second.register()
    assert records(database, WorkerCycle)[0]["state"] == "running"
    connection = first._lease.connection
    pid = connection.scalar(text("SELECT pg_backend_pid()"))
    connection.commit()
    with database.transaction() as session:
        assert session.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
    second.recover_stale_cycles()
    cycle = records(database, WorkerCycle)[0]
    assert cycle["state"] == "abandoned" and cycle["duration_ms"] is None
    assert not cycle["telemetry_complete"]
    assert all(row["state"] == "missing" and row["duration_ms"] is None for row in records(database, WorkerCycleSource))
    owner = next(row for row in records(database, WorkerInstance) if row["id"] == first.instance_id)
    assert owner["state"] == "stopped" and owner["last_cycle_outcome"] == "abandoned"
    probe = second.ownership.acquire(first.instance_id)
    assert probe is not None
    probe.close()
    wire_upcoming(monkeypatch, business_db, {})
    expected = upcoming_game_worker.run_once()
    try:
        with first.process():
            assert upcoming_game_worker.run_once() == expected
        assert not first.enabled
        assert first._lease is None
        assert len([r for r in caplog.records if "Worker telemetry unavailable" in r.message]) == 1
    finally:
        first.shutdown()
        second.shutdown()


def test_two_recoverers_hold_target_lock_through_single_abandonment(database, migrated, monkeypatch):
    first = recorder(database)
    first.register()
    first.start_cycle()
    make_stale(database, first)
    other_database = scoped_database(migrated[1], migrated[2])
    second, third = recorder(database), recorder(other_database)
    second.register()
    third.register()
    first._lease.close(discard=True)
    barrier = Barrier(2)
    outcomes = []
    probe = WorkerOwnership(database)
    for telemetry in (second, third):
        operation = telemetry.service.abandon_cycle
        def abandon(*args, _operation=operation, **kwargs):
            outcome = _operation(*args, **kwargs)
            outcomes.append(outcome)
            return outcome
        monkeypatch.setattr(telemetry.service, "abandon_cycle", abandon)
    def recover(telemetry):
        barrier.wait(timeout=5)
        telemetry.recover_stale_cycles()
        assert telemetry.enabled
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(recover, (second, third)))
        assert outcomes.count(True) == 1
        assert records(database, WorkerCycle)[0]["state"] == "abandoned"
        lease = probe.acquire(first.instance_id)
        assert lease is not None
        lease.close()
    finally:
        first.shutdown()
        second.shutdown()
        third.shutdown()
        probe.dispose()
        other_database.dispose()


def test_failed_abandonment_releases_target_ownership_without_mutation(database, monkeypatch):
    first, second = recorder(database), recorder(database)
    first.register()
    first.start_cycle()
    make_stale(database, first)
    second.register()
    first._lease.close(discard=True)
    before = records(database, WorkerCycleSource), records(database, WorkerCycle), records(database, WorkerInstance)
    operation = second.service._cycle
    def fail(*args, **kwargs):
        assert second.ownership.acquire(first.instance_id) is None
        raise TelemetryError("storage_unavailable")
    monkeypatch.setattr(second.service, "_cycle", fail)
    second.recover_stale_cycles()
    assert not second.enabled
    assert (records(database, WorkerCycleSource), records(database, WorkerCycle), records(database, WorkerInstance)) == before
    probe = WorkerOwnership(database)
    try:
        lease = probe.acquire(first.instance_id)
        assert lease is not None
        lease.close()
    finally:
        probe.dispose()
        first.shutdown()
        second.shutdown()


@pytest.mark.parametrize("boundary", ["connect", "lock_sql", "unlock_sql", "retention_check"])
def test_real_ownership_sql_failures_are_sanitized_and_cleaned(
    database, business_db, monkeypatch, caplog, boundary,
):
    from app.workers import upcoming_game_worker
    from sqlalchemy.engine import Connection, Engine
    wire_upcoming(monkeypatch, business_db, {})
    expected = upcoming_game_worker.run_once()
    telemetry = recorder(database)
    execute = Connection.execute
    scalar = Connection.scalar
    connect = Engine.connect
    def failing_execute(connection, statement, *args, **kwargs):
        sql = str(statement)
        if (
            (boundary == "lock_sql" and "pg_try_advisory_lock" in sql)
            or (boundary == "unlock_sql" and "pg_advisory_unlock" in sql)
            or (boundary == "retention_check" and "FROM pg_locks" in sql)
        ):
            raise SQLAlchemyError("private credentials")
        return execute(connection, statement, *args, **kwargs)
    def failing_connect(engine):
        from sqlalchemy.pool import NullPool
        if isinstance(engine.pool, NullPool):
            raise SQLAlchemyError("private connection URL")
        return connect(engine)
    def failing_scalar(connection, statement, *args, **kwargs):
        sql = str(statement)
        if (
            (boundary == "lock_sql" and "pg_try_advisory_lock" in sql)
            or (boundary == "retention_check" and "FROM pg_locks" in sql)
        ):
            raise SQLAlchemyError("private credentials")
        return scalar(connection, statement, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Connection, "execute", failing_execute)
        patch.setattr(Connection, "scalar", failing_scalar)
        if boundary == "connect":
            patch.setattr(Engine, "connect", failing_connect)
        with telemetry.process():
            assert upcoming_game_worker.run_once() == expected
    assert not telemetry.enabled and telemetry._lease is None
    messages = [r.message for r in caplog.records if "Worker telemetry unavailable" in r.message]
    assert len(messages) == 1 and "private" not in messages[0]
    probe = WorkerOwnership(database)
    try:
        lease = probe.acquire(telemetry.instance_id)
        assert lease is not None
        lease.close()
    finally:
        probe.dispose()


def test_ownership_key_is_namespaced_stable_signed_and_distinct():
    from uuid import UUID
    identifier = UUID("00000000-0000-0000-0000-000000000001")
    first = ownership_key(identifier)
    assert first == ownership_key(UUID(str(identifier)))
    assert -(1 << 63) <= first < (1 << 63)
    keys = {ownership_key(uuid4()) for _ in range(1000)}
    assert len(keys) == 1000 and first not in keys


def test_actual_ownership_statement_timeout_keeps_business_running(
    database, business_db, monkeypatch, caplog,
):
    from app.workers import upcoming_game_worker
    from sqlalchemy.engine import Connection
    wire_upcoming(monkeypatch, business_db, {})
    expected = upcoming_game_worker.run_once()
    telemetry = recorder(database)
    scalar = Connection.scalar
    def timeout(connection, statement, *args, **kwargs):
        if "pg_try_advisory_lock" in str(statement):
            return scalar(connection, text("SELECT pg_sleep(1)"))
        return scalar(connection, statement, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Connection, "scalar", timeout)
        with telemetry.process():
            assert upcoming_game_worker.run_once() == expected
    assert not telemetry.enabled and telemetry._lease is None
    assert records(database, WorkerInstance) == []
    assert len([r for r in caplog.records if "Worker telemetry unavailable" in r.message]) == 1


def test_expired_deadline_closes_connection_without_unlock_query(database, monkeypatch):
    from sqlalchemy import event
    telemetry = recorder(database)
    telemetry.register()
    telemetry.start_cycle()
    lease = telemetry._lease
    statements = []
    event.listen(lease.connection.engine, "before_cursor_execute",
                 lambda c, cur, sql, parameters, context, many: statements.append(sql))
    clock = [0.0]
    monkeypatch.setattr("app.workers.worker_instrumentation.time.monotonic", lambda: clock[0])
    telemetry.begin_cleanup()
    deadline = telemetry._cleanup_deadline
    clock[0] = 4.0
    telemetry.shutdown()
    assert telemetry._cleanup_deadline == deadline == 3.0
    assert statements == []
    assert lease.connection.closed and telemetry._lease is None
    assert records(database, WorkerCycle)[0]["state"] == "running"
    probe = WorkerOwnership(database)
    try:
        recovered = probe.acquire(telemetry.instance_id)
        assert recovered is not None
        recovered.close()
    finally:
        probe.dispose()


def snapshot(database):
    return tuple(records(database, model) for model in (WorkerCycleSource, WorkerCycle, WorkerInstance))


def test_transactional_recovery_conflicts_with_healthy_session_owner(database):
    owner = recorder(database)
    owner.register()
    owner.start_cycle()
    cycle_id = owner.cycle_id
    assert cycle_id is not None
    make_stale(database, owner)
    before = snapshot(database)
    now = datetime.now(UTC)
    try:
        assert owner.service.abandon_cycle(
            cycle_id, recovery_owner=owner.instance_id,
            stale_before=now - timedelta(hours=1), at=now,
        ) is False
        assert snapshot(database) == before
    finally:
        owner.shutdown()


@pytest.mark.parametrize("boundary", [
    "stale_recheck", "chronology", "source_update", "cycle_update", "instance_update", "commit",
    "connection_loss",
])
def test_recovery_transaction_failure_rolls_back_and_releases_proof(database, migrated, monkeypatch, boundary):
    from sqlalchemy import create_engine, event
    owner = recorder(database)
    owner.register()
    owner.start_cycle()
    cycle_id = owner.cycle_id
    assert cycle_id is not None
    make_stale(database, owner)
    owner._lease.close(discard=True)
    now = datetime.now(UTC)
    if boundary == "chronology":
        with database.transaction() as session:
            session.execute(update(WorkerCycleSource).where(
                WorkerCycleSource.cycle_id == owner.cycle_id,
            ).values(last_game_processed_at=now + timedelta(seconds=1)))
    before = snapshot(database)
    proof_seen = []
    probe = WorkerOwnership(database)
    killer = create_engine(migrated[1])
    service = WorkerTelemetryService(database)
    cycle = service._cycle
    def recheck(session, identifier):
        assert probe.acquire(owner.instance_id) is None
        proof_seen.append(session.scalar(text("SELECT pg_backend_pid()")))
        if boundary == "stale_recheck":
            raise TelemetryError("storage_unavailable")
        return cycle(session, identifier)
    monkeypatch.setattr(service, "_cycle", recheck)
    def after_write(connection, cursor, statement, parameters, context, many):
        target = {"source_update": "worker_cycle_sources", "cycle_update": "worker_cycles",
                  "instance_update": "worker_instances"}.get(boundary)
        if target and statement.startswith("UPDATE " + target):
            raise SQLAlchemyError("private fault after mutation")
    def before_commit(connection):
        if boundary == "commit":
            raise SQLAlchemyError("private commit fault")
        if boundary == "connection_loss":
            with killer.begin() as other:
                assert other.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": proof_seen[-1]})
    event.listen(database.engine, "after_cursor_execute", after_write)
    event.listen(database.engine, "commit", before_commit)
    try:
        with pytest.raises(TelemetryError) as caught:
            service.abandon_cycle(
                cycle_id, recovery_owner=owner.instance_id,
                stale_before=now - timedelta(hours=1),
                at=now,
            )
        assert caught.value.code in {"storage_unavailable", "invalid_input"}
    finally:
        event.remove(database.engine, "after_cursor_execute", after_write)
        event.remove(database.engine, "commit", before_commit)
        monkeypatch.setattr(service, "_cycle", cycle)
        killer.dispose()
    try:
        assert len(proof_seen) == 1
        assert snapshot(database) == before
        lease = probe.acquire(owner.instance_id)
        assert lease is not None
        lease.close()
        assert service.abandon_cycle(
            cycle_id, recovery_owner=owner.instance_id,
            stale_before=now - timedelta(hours=1), at=now + timedelta(seconds=2),
        ) is True
        assert records(database, WorkerCycle)[0]["state"] == "abandoned"
        lease = probe.acquire(owner.instance_id)
        assert lease is not None
        lease.close()
    finally:
        owner.shutdown()
        probe.dispose()


def test_terminal_target_recovery_false_releases_transaction_lock(database):
    owner = recorder(database)
    owner.register()
    owner.start_cycle()
    cycle_id = owner.cycle_id
    assert cycle_id is not None
    make_stale(database, owner)
    owner._lease.close(discard=True)
    now = datetime.now(UTC)
    owner.service.complete_cycle(
        cycle_id, state="failed", finished_at=now, duration_ms=1, telemetry_complete=False,
    )
    before = snapshot(database)
    assert owner.service.abandon_cycle(
        cycle_id, recovery_owner=owner.instance_id, stale_before=now, at=now,
    ) is False
    assert snapshot(database) == before
    probe = WorkerOwnership(database)
    try:
        lease = probe.acquire(owner.instance_id)
        assert lease is not None
        lease.close()
    finally:
        owner.shutdown()
        probe.dispose()


@pytest.mark.parametrize("boundary", ["connected", "acquired", "handoff", "registration", "registered", "recovery"])
@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, TelemetryError, SQLAlchemyError])
def test_real_startup_failure_releases_ownership_and_preserves_exit(
    database, monkeypatch, boundary, error_type,
):
    from sqlalchemy.engine import Connection
    telemetry = recorder(database)
    if boundary == "recovery":
        owner = recorder(database)
        owner.register()
        owner.start_cycle()
        make_stale(database, owner)
        owner._lease.close(discard=True)
    error = error_type(23 if error_type is SystemExit else "storage_unavailable")
    connections = []
    scalar, commit, execute = Connection.scalar, Connection.commit, Connection.execute
    register = telemetry.service.register_instance
    acquire = telemetry.ownership.acquire
    def acquiring(connection, statement, *args, **kwargs):
        if "pg_try_advisory_lock" in str(statement):
            connections.append(connection)
            if boundary == "connected":
                raise error
        return scalar(connection, statement, *args, **kwargs)
    def committing(connection):
        if boundary == "acquired" and connection in connections:
            raise error
        return commit(connection)
    def registering(*args, **kwargs):
        register(*args, **kwargs)
        raise error
    def executing(connection, statement, *args, **kwargs):
        result = execute(connection, statement, *args, **kwargs)
        if boundary == "registration" and str(statement).startswith("INSERT INTO worker_instances"):
            raise error
        return result
    def recovering(*args, **kwargs):
        raise error
    def handoff(*args, **kwargs):
        acquire(*args, **kwargs)
        raise error
    monkeypatch.setattr("app.workers.worker_instrumentation.time.monotonic", lambda: 100.0)
    with monkeypatch.context() as patch:
        patch.setattr(Connection, "scalar", acquiring)
        patch.setattr(Connection, "commit", committing)
        patch.setattr(Connection, "execute", executing)
        if boundary == "registered":
            patch.setattr(telemetry.service, "register_instance", registering)
        if boundary == "recovery":
            patch.setattr(telemetry.service, "abandon_cycle", recovering)
        if boundary == "handoff":
            patch.setattr(telemetry.ownership, "acquire", handoff)
        if error_type in {TelemetryError, SQLAlchemyError}:
            with telemetry.process():
                assert not telemetry.enabled
        else:
            with pytest.raises(error_type) as caught:
                with telemetry.process():
                    pytest.fail("Startup interruption entered business work")
            assert caught.value is error
            if error_type is SystemExit:
                assert caught.value.code == 23
    assert telemetry._cleanup_deadline == 103.0
    assert connections and all(connection.closed for connection in connections)
    assert telemetry._lease is None
    rows = [row for row in records(database, WorkerInstance) if row["id"] == telemetry.instance_id]
    assert all(row["state"] == "starting" and row["stopped_at"] is None for row in rows)
    if boundary in {"connected", "acquired", "handoff", "registration"}:
        assert rows == []
    probe = WorkerOwnership(database)
    try:
        lease = probe.acquire(telemetry.instance_id)
        assert lease is not None
        lease.close()
    finally:
        probe.dispose()
        if boundary == "recovery":
            owner.shutdown()


def test_verification_does_not_increment_session_lock_count(database):
    ownership = WorkerOwnership(database)
    contender = WorkerOwnership(database)
    identifier = uuid4()
    lease = ownership.acquire(str(identifier))
    try:
        for _ in range(50):
            lease.check()
            assert not lease.connection.in_transaction()
        assert contender.acquire(identifier) is None
        assert lease.connection.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": ownership_key(identifier)})
        lease.connection.commit()
        other = contender.acquire(identifier)
        assert other is not None
        other.close()
    finally:
        lease.close(discard=True)
        ownership.dispose()
        contender.dispose()


def test_overlapping_recovery_transactions_acquire_exactly_one_proof(database, migrated, monkeypatch):
    from sqlalchemy.orm import Session
    owner = recorder(database)
    owner.register()
    owner.start_cycle()
    cycle_id = owner.cycle_id
    assert cycle_id is not None
    make_stale(database, owner)
    owner._lease.close(discard=True)
    other = scoped_database(migrated[1], migrated[2])
    barrier = Barrier(2)
    acquired = []
    scalar = Session.scalar
    def proof(session, statement, *args, **kwargs):
        result = scalar(session, statement, *args, **kwargs)
        if "pg_try_advisory_xact_lock" in str(statement):
            acquired.append(result)
            barrier.wait(timeout=5)
        return result
    monkeypatch.setattr(Session, "scalar", proof)
    now = datetime.now(UTC)
    def recover(database):
        return WorkerTelemetryService(database).abandon_cycle(
            cycle_id, recovery_owner=owner.instance_id,
            stale_before=now - timedelta(hours=1), at=now,
        )
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(recover, (database, other)))
        assert sorted(acquired) == [False, True]
        assert sorted(outcomes) == [False, True]
        assert records(database, WorkerCycle)[0]["state"] == "abandoned"
        assert all(row["state"] == "missing" for row in records(database, WorkerCycleSource))
    finally:
        other.dispose()
        owner.shutdown()


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_startup_cleanup_failure_does_not_replace_original_exit(database, monkeypatch, error_type):
    telemetry = recorder(database)
    original = error_type(23)
    connections = []
    register = telemetry.service.register_instance
    def interrupted(*args, **kwargs):
        register(*args, **kwargs)
        connections.append(telemetry._lease.connection)
        close = telemetry._lease.close
        def failed_cleanup(*args, **kwargs):
            close(*args, **kwargs)
            raise SystemExit(99)
        monkeypatch.setattr(telemetry._lease, "close", failed_cleanup)
        raise original
    monkeypatch.setattr(telemetry.service, "register_instance", interrupted)
    with pytest.raises(error_type) as caught:
        with telemetry.process():
            pytest.fail("Startup interruption entered business work")
    assert caught.value is original
    assert telemetry._cleanup_deadline is not None
    assert connections[0].closed
    assert records(database, WorkerInstance)[0]["state"] == "starting"
    probe = WorkerOwnership(database)
    try:
        lease = probe.acquire(telemetry.instance_id)
        assert lease is not None
        lease.close()
    finally:
        probe.dispose()
