from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
import httpx
from pydantic import ValidationError
import pytest
import requests
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError

from app.database.telemetry_session import TelemetryConfig, TelemetryDatabase, TelemetryError
from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import SOURCE_COUNTERS, WorkerCycleSource
from app.models.worker_instance import WorkerInstance
from app.services.worker_telemetry_service import SourceIdentity, WorkerTelemetryService
from scripts import prune_worker_telemetry as cli
from settings.base import BaseAppSettings


TABLES = (WorkerInstance.__table__, WorkerCycle.__table__, WorkerCycleSource.__table__)
NOW = datetime(2026, 10, 6, 12, tzinfo=UTC)
SOURCE = SourceIdentity("NBA", "NBA", "odds_api", "basketball_nba")


@pytest.fixture(autouse=True)
def block_http(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("External HTTP is forbidden in telemetry tests")
    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(httpx.Client, "send", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)


@pytest.fixture
def database(tmp_path):
    database = TelemetryDatabase(f"sqlite:///{tmp_path / 'telemetry.sqlite'}", TelemetryConfig(enabled=True))
    for table in TABLES:
        table.create(database.engine)
    yield database
    database.dispose()


@pytest.fixture
def service(database):
    return WorkerTelemetryService(database)


def register(service, *, at=NOW, sources=(SOURCE,), instance_id=None):
    identifier = instance_id or uuid4()
    assert service.register_instance(
        identifier, worker_name="upcoming-game-worker", started_at=at,
        poll_seconds=3600, heartbeat_seconds=60, schedule_mode="after_completion",
        sources=sources,
    ) == identifier
    return identifier


def cycle(service, instance, *, at=NOW, sources=(SOURCE,)):
    identifier = uuid4()
    service.begin_cycle(instance, identifier, started_at=at, expected_sources=len(sources))
    ids = service.register_sources(identifier, sources)
    return identifier, ids


def finish(service, identifier, source_ids, *, at=NOW, state="succeeded"):
    for source_id in source_ids:
        service.transition_source(identifier, source_id, state="running", at=at)
        service.transition_source(identifier, source_id, state="succeeded", at=at, duration_ms=0, counters={"errors": 0, "fetched": 0})
    service.complete_cycle(identifier, state=state, finished_at=at, duration_ms=0)


def test_lazy_disabled_performs_no_database_work(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Disabled telemetry touched a database")
    monkeypatch.setattr("app.database.telemetry_session.create_engine", forbidden)
    service = WorkerTelemetryService(TelemetryDatabase("postgresql://invalid", TelemetryConfig()))
    assert service.register_instance(uuid4(), worker_name="invalid", started_at=NOW, poll_seconds=1, heartbeat_seconds=1, schedule_mode="invalid", sources=()) is None
    assert service.update_heartbeat(uuid4(), NOW) is None
    assert service.update_progress(uuid4(), NOW) is None
    assert service.begin_cycle(uuid4(), uuid4(), started_at=NOW, expected_sources=0) is None
    assert service.register_sources(uuid4(), ()) is None
    assert service.transition_source(uuid4(), 1, state="failed", at=NOW) is None
    assert service.complete_cycle(uuid4(), state="failed", finished_at=NOW, duration_ms=0) is None
    assert service.abandon_cycle(uuid4(), stale_before=NOW, at=NOW) is None
    assert service.stop_instance(uuid4(), NOW) is None
    assert service.increment_failure_count(uuid4(), expected_count=0) is None
    assert service.prune_history(at=NOW).enabled is False


def test_registration_retry_multiple_instances_and_safe_manifest(service, database):
    first = register(service)
    register(service, instance_id=first)
    second = register(service)
    assert second != first
    with database.transaction() as db:
        assert len(db.execute(select(WorkerInstance.__table__)).all()) == 2
    with pytest.raises(TelemetryError, match="conflict"):
        register(service, instance_id=first, at=NOW + timedelta(seconds=1))
    with pytest.raises(TelemetryError, match="invalid_input"):
        register(service, sources=(SourceIdentity("NBA", "NBA", "odds_api", "https://secret/path"),))
    with pytest.raises(TelemetryError, match="invalid_input"):
        register(service, sources=(SOURCE, SOURCE))


def test_heartbeat_is_not_progress(service, database):
    instance = register(service)
    assert service.update_heartbeat(instance, NOW + timedelta(seconds=60))
    assert service.update_progress(instance, NOW + timedelta(seconds=30))
    assert not service.update_heartbeat(instance, NOW)
    with database.transaction() as db:
        row = db.execute(select(WorkerInstance.__table__)).mappings().one()
        assert row["heartbeat_at"].replace(tzinfo=UTC) == NOW + timedelta(seconds=60)
        assert row["progress_at"].replace(tzinfo=UTC) == NOW + timedelta(seconds=30)


def test_cycle_sequence_retry_and_running_constraint(service, database):
    instance = register(service)
    identifier, sources = cycle(service, instance)
    assert service.begin_cycle(instance, identifier, started_at=NOW, expected_sources=1) == 1
    with pytest.raises(TelemetryError):
        cycle(service, instance)
    with pytest.raises(IntegrityError), database.engine.begin() as connection:
        connection.execute(insert(WorkerCycle.__table__).values(
            id=uuid4(), instance_id=instance, sequence=2, state="running", started_at=NOW, expected_sources=1,
        ))
    finish(service, identifier, sources)
    next_id, _ = cycle(service, instance)
    with database.transaction() as db:
        assert db.scalar(select(WorkerCycle.sequence).where(WorkerCycle.id == next_id)) == 2


def test_source_retry_null_zero_and_terminal_guard(service, database):
    instance = register(service)
    identifier, ids = cycle(service, instance)
    assert service.register_sources(identifier, (SOURCE,)) == ids
    source_id = ids[0]
    assert service.transition_source(identifier, source_id, state="running", at=NOW)
    assert not service.transition_source(identifier, source_id, state="running", at=NOW)
    assert service.transition_source(identifier, source_id, state="succeeded", at=NOW, duration_ms=0, counters={"fetched": 0})
    assert not service.transition_source(identifier, source_id, state="succeeded", at=NOW, duration_ms=0, counters={"fetched": 0})
    with database.transaction() as db:
        row = db.execute(select(WorkerCycleSource.__table__)).mappings().one()
        assert row["fetched"] == 0
        assert row["publications_created"] is None
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(identifier, source_id, state="succeeded", at=NOW, duration_ms=0, counters={"fetched": 1})
    with pytest.raises(TelemetryError, match="illegal_transition"):
        service.transition_source(identifier, source_id, state="failed", at=NOW, duration_ms=0)


def test_running_source_updates_are_absolute_monotonic_and_idempotent(service, database):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW)
    assert service.transition_source(identifier, ids[0], state="running", at=NOW + timedelta(seconds=1), counters={"fetched": 2})
    assert not service.transition_source(identifier, ids[0], state="running", at=NOW + timedelta(seconds=2), counters={"fetched": 2})
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(identifier, ids[0], state="running", at=NOW, counters={"fetched": 1})
    with database.transaction() as db:
        assert db.scalar(select(WorkerCycleSource.fetched)) == 2


def test_source_cannot_start_before_cycle(service):
    identifier, ids = cycle(service, register(service))
    with pytest.raises(TelemetryError, match="invalid_input"):
        service.transition_source(identifier, ids[0], state="running", at=NOW - timedelta(seconds=1))


@pytest.mark.parametrize("counter", SOURCE_COUNTERS)
@pytest.mark.parametrize("value", [0, None])
def test_terminal_update_cannot_decrease_recorded_counters(service, database, counter, value):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW, counters={counter: 5})
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(identifier, ids[0], state="failed", at=NOW, duration_ms=0, counters={counter: value})
    with database.transaction() as db:
        row = db.execute(select(WorkerCycleSource.__table__)).mappings().one()
        assert row["state"] == "running"
        assert row[counter] == 5


def test_terminal_preserves_failure_evidence_and_retries(service, database):
    identifier, ids = cycle(service, register(service))
    service.transition_source(
        identifier, ids[0], state="running", at=NOW,
        counters={"fetched": 5, "errors": 2}, error_code="publication_failed",
    )
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(
            identifier, ids[0], state="succeeded", at=NOW, duration_ms=0,
            counters={"fetched": 0, "errors": 0}, error_code=None,
        )
    with pytest.raises(TelemetryError, match="incomplete_source"):
        service.transition_source(identifier, ids[0], state="succeeded", at=NOW, duration_ms=0)
    assert service.transition_source(identifier, ids[0], state="partial", at=NOW, duration_ms=0)
    assert not service.transition_source(identifier, ids[0], state="partial", at=NOW, duration_ms=0)
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(identifier, ids[0], state="partial", at=NOW, duration_ms=0, counters={"fetched": 6})
    with pytest.raises(TelemetryError, match="illegal_transition"):
        service.transition_source(identifier, ids[0], state="failed", at=NOW, duration_ms=0)
    with pytest.raises(TelemetryError, match="incomplete_cycle"):
        service.complete_cycle(identifier, state="succeeded", finished_at=NOW, duration_ms=0)
    service.complete_cycle(identifier, state="partial", finished_at=NOW, duration_ms=0)
    with database.transaction() as db:
        row = db.execute(select(WorkerCycleSource.__table__)).mappings().one()
        assert (row["fetched"], row["errors"], row["error_code"]) == (5, 2, "publication_failed")
        result = db.execute(select(WorkerCycle.__table__)).mappings().one()
        assert result["state"] == "partial"
        assert result["failed_sources"] == 1
        assert result["telemetry_complete"] is True


@pytest.mark.parametrize("evidence", [
    {"error_code": "publication_failed"},
    {"counters": {"errors": 1}},
    {"counters": {"publications_failed": 1}},
])
def test_retained_failure_prevents_source_success(service, evidence):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW, **evidence)
    with pytest.raises(TelemetryError, match="incomplete_source"):
        service.transition_source(identifier, ids[0], state="succeeded", at=NOW, duration_ms=0)


@pytest.mark.parametrize("code", [None, "provider_unavailable"])
def test_recorded_error_cannot_be_cleared_or_replaced(service, code):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW, error_code="publication_failed")
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(identifier, ids[0], state="failed", at=NOW, duration_ms=0, error_code=code)


@pytest.mark.parametrize("field", [
    "last_game_processed_at", "latest_odds_observed_at", "latest_prediction_published_at",
])
def test_out_of_order_latest_observations_merge_maximum(service, database, field):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW)
    latest = NOW + timedelta(seconds=20)
    assert service.transition_source(identifier, ids[0], state="running", at=latest, timestamps={field: latest})
    assert not service.transition_source(
        identifier, ids[0], state="running", at=NOW + timedelta(seconds=10),
        timestamps={field: NOW + timedelta(seconds=10)},
    )
    assert not service.transition_source(identifier, ids[0], state="running", at=latest, timestamps={field: latest})
    with database.transaction() as db:
        assert db.scalar(select(WorkerCycleSource.__table__.c[field])).replace(tzinfo=UTC) == latest


def test_game_date_bounds_merge_minimum_and_maximum(service, database):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW,
                              timestamps={"game_date_min": NOW, "game_date_max": NOW})
    earliest, latest = NOW - timedelta(days=1), NOW + timedelta(days=1)
    service.transition_source(identifier, ids[0], state="running", at=NOW,
                              timestamps={"game_date_min": earliest, "game_date_max": latest})
    assert not service.transition_source(identifier, ids[0], state="running", at=NOW,
                                         timestamps={"game_date_min": NOW, "game_date_max": NOW})
    with database.transaction() as db:
        row = db.execute(select(WorkerCycleSource.__table__)).mappings().one()
        assert row["game_date_min"].replace(tzinfo=UTC) == earliest
        assert row["game_date_max"].replace(tzinfo=UTC) == latest


@pytest.mark.parametrize("operation", ["abandon", "complete"])
def test_automatic_missing_preserves_errors_and_unknown_duration(service, database, operation):
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW, error_code="publication_failed")
    if operation == "abandon":
        assert service.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=1), at=NOW + timedelta(seconds=2))
    else:
        service.complete_cycle(identifier, state="failed", finished_at=NOW + timedelta(seconds=2), duration_ms=100)
    with database.transaction() as db:
        row = db.execute(select(WorkerCycleSource.__table__)).mappings().one()
        assert row["state"] == "missing"
        assert row["duration_ms"] is None
        assert row["error_code"] == "publication_failed"
        result = db.execute(select(WorkerCycle.__table__)).mappings().one()
        assert result["telemetry_complete"] is False
        assert result["duration_ms"] == (None if operation == "abandon" else 100)


def test_backward_abandonment_is_rejected_without_fabricated_duration(service, database):
    identifier, _ = cycle(service, register(service))
    with pytest.raises(TelemetryError, match="invalid_input"):
        service.abandon_cycle(identifier, stale_before=NOW - timedelta(seconds=2), at=NOW - timedelta(seconds=1))
    with database.transaction() as db:
        result = db.execute(select(WorkerCycle.__table__)).mappings().one()
        assert result["state"] == "running"
        assert result["duration_ms"] is None


SOURCE_LIFECYCLE_TIMESTAMPS = (
    "started_at", "finished_at", "last_game_processed_at",
    "latest_odds_observed_at", "latest_prediction_published_at",
)


def assert_abandonment_chronology(service, database, field, seconds_after):
    sources = (
        SOURCE, SourceIdentity("NBA", "NBA", "odds_api", "second"),
        SourceIdentity("NBA", "NBA", "odds_api", "third"),
    )
    instance = register(service, sources=sources)
    identifier, ids = cycle(service, instance, sources=sources)
    latest = NOW + timedelta(seconds=20)
    service.transition_source(identifier, ids[0], state="running", at=NOW)
    service.transition_source(
        identifier, ids[0], state="succeeded",
        at=latest if field == "finished_at" else NOW, duration_ms=123,
    )
    if field == "started_at":
        service.transition_source(identifier, ids[1], state="running", at=latest)
    else:
        service.transition_source(
            identifier, ids[1], state="running", at=NOW,
            counters={"fetched": 5, "errors": 2}, error_code="publication_failed",
            timestamps={field: latest} if field not in {"started_at", "finished_at"} else None,
        )

    def snapshot():
        with database.transaction() as db:
            return (
                dict(db.execute(select(WorkerInstance.__table__).where(WorkerInstance.id == instance)).mappings().one()),
                dict(db.execute(select(WorkerCycle.__table__).where(WorkerCycle.id == identifier)).mappings().one()),
                [dict(row) for row in db.execute(
                    select(WorkerCycleSource.__table__).where(WorkerCycleSource.cycle_id == identifier)
                    .order_by(WorkerCycleSource.id)
                ).mappings()],
            )

    before = snapshot()
    with pytest.raises(TelemetryError, match="invalid_input"):
        service.abandon_cycle(
            identifier, stale_before=NOW + timedelta(seconds=5), at=NOW + timedelta(seconds=10),
        )
    assert snapshot() == before
    assert before[1]["state"] == "running"
    assert before[1]["finished_at"] is None
    at = latest + timedelta(seconds=seconds_after)
    assert service.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=5), at=at)
    after = snapshot()
    assert after[0]["state"] == "stopped"
    assert after[1]["state"] == "abandoned"
    assert after[1]["duration_ms"] is None
    assert after[1]["telemetry_complete"] is False
    assert after[1]["finished_at"].replace(tzinfo=UTC) == at
    assert after[2][0] == before[2][0]
    for original, missing in zip(before[2][1:], after[2][1:]):
        assert missing["state"] == "missing"
        assert missing["duration_ms"] is None
        assert missing["finished_at"].replace(tzinfo=UTC) == at
        for key, value in original.items():
            if key not in {"state", "finished_at", "duration_ms", "error_code"}:
                assert missing[key] == value
        if original["error_code"] is not None:
            assert missing["error_code"] == original["error_code"]
    assert not service.abandon_cycle(identifier, stale_before=at, at=at)


@pytest.mark.parametrize("field", SOURCE_LIFECYCLE_TIMESTAMPS)
@pytest.mark.parametrize("seconds_after", [0, 1])
def test_abandonment_rejects_backward_source_evidence_atomically(service, database, field, seconds_after):
    assert_abandonment_chronology(service, database, field, seconds_after)


def assert_scheduled_game_dates_do_not_block_abandonment(service):
    identifier, ids = cycle(service, register(service))
    service.transition_source(
        identifier, ids[0], state="running", at=NOW,
        timestamps={"game_date_min": NOW + timedelta(days=1), "game_date_max": NOW + timedelta(days=2)},
    )
    assert service.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=1), at=NOW + timedelta(seconds=2))


def test_scheduled_game_dates_are_not_lifecycle_occurrences(service):
    assert_scheduled_game_dates_do_not_block_abandonment(service)


@pytest.mark.parametrize("state", ["succeeded", "partial", "failed"])
def test_cycle_completion_and_retry(service, database, state):
    instance = register(service)
    identifier, ids = cycle(service, instance)
    if state == "succeeded":
        finish(service, identifier, ids)
    else:
        assert service.complete_cycle(identifier, state=state, finished_at=NOW, duration_ms=0)
    assert not service.complete_cycle(identifier, state=state, finished_at=NOW, duration_ms=0)
    with database.transaction() as db:
        row = db.execute(select(WorkerInstance.__table__)).mappings().one()
        assert row["state"] == "idle"
        assert (row["last_success_at"] is not None) == (state == "succeeded")
    assert service.register_sources(identifier, (SOURCE,)) == ids


def test_success_requires_complete_error_free_evidence(service):
    instance = register(service)
    identifier, _ = cycle(service, instance)
    with pytest.raises(TelemetryError, match="incomplete_cycle"):
        service.complete_cycle(identifier, state="succeeded", finished_at=NOW, duration_ms=0)


def test_abandonment_rechecks_heartbeat_and_preserves_terminal(service, database):
    old = NOW - timedelta(hours=2)
    instance = register(service, at=old)
    identifier, _ = cycle(service, instance, at=old)
    service.update_heartbeat(instance, NOW)
    assert not service.abandon_cycle(identifier, stale_before=NOW - timedelta(minutes=1), at=NOW)
    assert service.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=1), at=NOW + timedelta(seconds=2))
    assert not service.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=3), at=NOW + timedelta(seconds=4))
    with database.transaction() as db:
        assert db.scalar(select(WorkerCycle.state)) == "abandoned"
        assert db.scalar(select(WorkerCycleSource.state)) == "missing"
    with pytest.raises(TelemetryError, match="illegal_transition"):
        service.complete_cycle(identifier, state="failed", finished_at=NOW + timedelta(seconds=5), duration_ms=0)


def test_stop_and_failure_counter(service):
    instance = register(service)
    assert service.increment_failure_count(instance, expected_count=0) == 1
    assert service.increment_failure_count(instance, expected_count=0) == 1
    assert service.increment_failure_count(instance, expected_count=1) == 2
    assert service.stop_instance(instance, NOW)
    assert not service.stop_instance(instance, NOW)
    with pytest.raises(TelemetryError, match="illegal_transition"):
        service.update_heartbeat(instance, NOW)


@pytest.mark.parametrize("field,value", [
    ("state", "invalid"), ("worker_name", "invalid"), ("poll_seconds", 0),
    ("heartbeat_seconds", -1), ("schedule_mode", "invalid"), ("source_manifest", {}),
    ("heartbeat_at", NOW - timedelta(seconds=1)), ("telemetry_failures", -1),
    ("last_success_duration_ms", -1), ("stopped_at", NOW),
    ("last_success_duration_ms", 0), ("last_success_at", NOW),
    ("last_cycle_outcome", "failed"),
])
def test_instance_database_constraints(database, field, value):
    values = dict(
        id=uuid4(), worker_name="upcoming-game-worker", state="starting", started_at=NOW,
        heartbeat_at=NOW, progress_at=NOW, poll_seconds=3600, heartbeat_seconds=60,
        schedule_mode="after_completion", source_manifest=[],
    )
    values[field] = value
    with pytest.raises(IntegrityError), database.engine.begin() as connection:
        connection.execute(insert(WorkerInstance.__table__).values(**values))


@pytest.mark.parametrize("changes", [
    {"state": "bad"}, {"sequence": 0}, {"expected_sources": -1},
    {"completed_sources": 2}, {"failed_sources": 1},
    {"state": "succeeded"}, {"finished_at": NOW}, {"duration_ms": -1},
    {"state": "failed", "finished_at": NOW - timedelta(seconds=1), "duration_ms": 0},
])
def test_cycle_database_constraints(service, database, changes):
    instance = register(service)
    values = dict(id=uuid4(), instance_id=instance, sequence=1, state="running", started_at=NOW, expected_sources=1)
    values.update(changes)
    with pytest.raises(IntegrityError), database.engine.begin() as connection:
        connection.execute(insert(WorkerCycle.__table__).values(**values))


@pytest.mark.parametrize("counter", SOURCE_COUNTERS)
def test_source_counter_constraints(service, database, counter):
    instance = register(service)
    _, ids = cycle(service, instance)
    with pytest.raises(IntegrityError), database.engine.begin() as connection:
        connection.execute(update(WorkerCycleSource.__table__).where(WorkerCycleSource.id == ids[0]).values({counter: -1}))


@pytest.mark.parametrize("changes", [
    {"state": "bad"}, {"state": "running"}, {"state": "succeeded"},
    {"duration_ms": 0}, {"game_date_min": NOW, "game_date_max": NOW - timedelta(seconds=1)},
])
def test_source_timestamp_state_constraints(service, database, changes):
    _, ids = cycle(service, register(service))
    with pytest.raises(IntegrityError), database.engine.begin() as connection:
        connection.execute(update(WorkerCycleSource.__table__).where(WorkerCycleSource.id == ids[0]).values(**changes))


@pytest.mark.parametrize("kwargs", [
    {"error_code": "password=secret"}, {"counters": {"customer": 1}},
    {"counters": {"fetched": -1}}, {"timestamps": {"path": NOW}},
    {"at": datetime(2026, 1, 1)},
])
def test_service_rejects_unsafe_input(service, kwargs):
    identifier, ids = cycle(service, register(service))
    arguments = dict(state="running", at=NOW)
    arguments.update(kwargs)
    with pytest.raises(TelemetryError):
        service.transition_source(identifier, ids[0], **arguments)


def test_storage_failure_is_sanitized_and_business_transaction_independent(database):
    with database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE business_probe (id INTEGER PRIMARY KEY)"))
    from sqlalchemy import create_engine
    business_engine = create_engine(database.engine.url)
    bad_database = TelemetryDatabase(str(database.engine.url), TelemetryConfig(enabled=True))
    try:
        with business_engine.begin() as business:
            business.execute(text("INSERT INTO business_probe VALUES (1)"))
            with pytest.raises(TelemetryError) as failure:
                WorkerTelemetryService(bad_database).increment_failure_count(uuid4(), expected_count=0)
            assert failure.value.code == "not_found"
            assert business.scalar(text("SELECT count(*) FROM business_probe")) == 1
        with business_engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM business_probe")) == 1
        with pytest.raises(TelemetryError) as failure:
            with bad_database.transaction() as telemetry:
                telemetry.execute(text("SELECT password_secret FROM nonexistent_table"))
        assert str(failure.value) == "Telemetry operation failed: storage_unavailable"
    finally:
        bad_database.dispose()
        business_engine.dispose()


def test_pool_exhaustion_and_disposal(database):
    old_engine = database.engine
    with old_engine.connect():
        with pytest.raises(TelemetryError, match="storage_unavailable"):
            with database.transaction() as session:
                session.execute(text("SELECT 1"))
    database.dispose()
    assert database._engine is None
    assert database.engine is not old_engine


@pytest.mark.parametrize("values", [
    {"enabled": "true"}, {"statement_timeout_ms": 0}, {"lock_timeout_ms": 0},
    {"pool_timeout_seconds": float("inf")}, {"connect_timeout_seconds": 0},
])
def test_direct_database_configuration_is_bounded(values):
    with pytest.raises(TelemetryError, match="invalid_configuration"):
        TelemetryConfig(**values)


def test_retention_dry_run_cascade_and_sequence_anchor(service, database):
    old = NOW - timedelta(days=40)
    instance = register(service, at=old)
    first, ids = cycle(service, instance, at=old)
    finish(service, first, ids, at=old)
    second, ids = cycle(service, instance, at=old)
    finish(service, second, ids, at=old)
    preview = service.prune_history(at=NOW, dry_run=True)
    assert (preview.cycles, preview.instances) == (1, 0)
    with database.transaction() as db:
        assert len(db.execute(select(WorkerCycle.id)).all()) == 2
    assert service.prune_history(at=NOW).cycles == 1
    with database.transaction() as db:
        assert len(db.execute(select(WorkerCycleSource.id)).all()) == 1
    third, ids = cycle(service, instance, at=old)
    with database.transaction() as db:
        assert db.scalar(select(WorkerCycle.sequence).where(WorkerCycle.id == third)) == 3
    assert service.prune_history(at=NOW).instances == 0
    finish(service, third, ids, at=old)
    service.stop_instance(instance, old)
    assert service.prune_history(at=NOW).instances == 1
    with database.transaction() as db:
        assert not db.execute(select(WorkerInstance.id)).all()
        assert not db.execute(select(WorkerCycleSource.id)).all()


def test_retention_cutoff_and_running_exclusion(service):
    old = NOW - timedelta(days=30)
    instance = register(service, at=old)
    identifier, ids = cycle(service, instance, at=old)
    finish(service, identifier, ids, at=old)
    service.stop_instance(instance, old)
    assert service.prune_history(at=NOW).cycles == 0
    assert service.prune_history(at=NOW + timedelta(seconds=1)).cycles == 1
    running = register(service, at=NOW - timedelta(days=40))
    cycle(service, running, at=NOW - timedelta(days=40))
    assert service.prune_history(at=NOW).cycles == 0


def test_cli_dry_run_error_and_batch_bounds(service, monkeypatch, capsys):
    monkeypatch.setattr(cli, "WorkerTelemetryService", lambda: service)
    assert cli.main(["--dry-run", "--batch-size", "10"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == dict(enabled=True, dry_run=True, lock_acquired=True, cycles=0, instances=0, batch_size=10)
    with pytest.raises(SystemExit) as error:
        cli.main(["--batch-size", "501"])
    assert error.value.code == 2
    capsys.readouterr()
    def fail(**_kwargs):
        raise TelemetryError("storage_unavailable")
    monkeypatch.setattr(service, "prune_history", fail)
    assert cli.main([]) == 1
    assert json.loads(capsys.readouterr().out) == {"error": "storage_unavailable"}


@pytest.mark.parametrize("field,value", [
    ("OPERATIONS_CYCLE_RETENTION_DAYS", 0), ("OPERATIONS_CYCLE_RETENTION_DAYS", 366),
    ("OPERATIONS_STARTUP_GRACE_SECONDS", 0), ("OPERATIONS_TELEMETRY_STATEMENT_TIMEOUT_MS", 0),
    ("OPERATIONS_TELEMETRY_LOCK_TIMEOUT_MS", 0), ("OPERATIONS_TELEMETRY_POOL_TIMEOUT_SECONDS", float("nan")),
    ("OPERATIONS_TELEMETRY_CONNECT_TIMEOUT_SECONDS", 11),
])
def test_settings_bounds(field, value):
    with pytest.raises(ValidationError):
        BaseAppSettings(
            _env_file=None, DATABASE_URL="sqlite://", SECRET_KEY="test", JWT_SECRET="test",
            ODDS_API_KEY="test", AUTH_DEMO_EMAIL="test@example.com", AUTH_DEMO_PASSWORD="test",
            **{field: value},
        )


def test_single_new_migration_head():
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["a9b2e4d7c031"]
    assert script.get_revision("e7b4c2d9a610").down_revision == "c8d2f6a109b4"
