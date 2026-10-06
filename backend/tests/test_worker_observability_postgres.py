from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.config import Config
from pathlib import Path
import pytest
from sqlalchemy import create_engine, event, inspect, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.database.telemetry_session import TelemetryConfig, TelemetryDatabase, TelemetryError
from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import WorkerCycleSource
from app.models.worker_instance import WorkerInstance
from app.services.worker_telemetry_service import CLEANUP_LOCK, WorkerTelemetryService
from test_worker_telemetry import NOW, SOURCE, TABLES, block_http, cycle, finish, register
from test_worker_telemetry import (
    SOURCE_LIFECYCLE_TIMESTAMPS, assert_abandonment_chronology,
    assert_scheduled_game_dates_do_not_block_abandonment,
)


def migration_config(connection):
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    config.attributes["connection"] = connection
    return config


def scoped_database(url, schema):
    database = TelemetryDatabase(url, TelemetryConfig(enabled=True))
    def search_path(connection, _record):
        cursor = connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        connection.commit()
        cursor.close()
    event.listen(database.engine, "connect", search_path)
    return database


@pytest.fixture
def postgres():
    target = os.environ.get("METRIC_TEST_POSTGRES_URL")
    if not target:
        pytest.skip("Disposable PostgreSQL URL not supplied")
    url = make_url(target)
    assert url.get_backend_name() == "postgresql"
    assert url.host in {"localhost", "127.0.0.1"}
    assert url.database == "metric_integrity_test"
    schema = f"telemetry_{uuid4().hex}"
    admin = create_engine(target, hide_parameters=True)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    database = scoped_database(target, schema)
    try:
        with database.engine.begin() as connection:
            for table in (Team.__table__, Game.__table__, Odds.__table__, Prediction.__table__, PredictionResult.__table__):
                table.create(connection)
            command.stamp(migration_config(connection), "c8d2f6a109b4")
        yield database, target, schema
    finally:
        database.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def migrated(postgres):
    database, _, _ = postgres
    with database.engine.begin() as connection:
        command.upgrade(migration_config(connection), "head")
    return postgres


def schema_snapshot(connection):
    inspector = inspect(connection)
    result = {}
    for table in inspector.get_table_names():
        if table in {"alembic_version", *(table.name for table in TABLES)}:
            continue
        result[table] = {
            "columns": [
                (column["name"], str(column["type"]), column["nullable"], column["default"])
                for column in inspector.get_columns(table)
            ],
            "pk": inspector.get_pk_constraint(table),
            "fk": inspector.get_foreign_keys(table),
            "unique": inspector.get_unique_constraints(table),
            "checks": inspector.get_check_constraints(table),
            "indexes": inspector.get_indexes(table),
        }
    return result


def telemetry_schema_definition(connection, schema):
    inspector = inspect(connection)
    definitions = {}
    for table in TABLES:
        name = table.name
        foreign_keys = inspector.get_foreign_keys(name, schema=schema)
        for foreign_key in foreign_keys:
            assert foreign_key["referred_schema"] in {None, schema}
            foreign_key["referred_schema"] = "telemetry"
        definitions[name] = {
            "columns": {
                column["name"]: (
                    column["type"].compile(dialect=connection.dialect),
                    column["nullable"], column["default"], column.get("identity"),
                )
                for column in inspector.get_columns(name, schema=schema)
            },
            "pk": inspector.get_pk_constraint(name, schema=schema),
            "checks": sorted(
                (check["name"], check["sqltext"])
                for check in inspector.get_check_constraints(name, schema=schema)
            ),
            "unique": sorted(
                (constraint["name"], tuple(constraint["column_names"]))
                for constraint in inspector.get_unique_constraints(name, schema=schema)
            ),
            "indexes": sorted(
                (
                    index["name"], index["unique"], tuple(index["column_names"]),
                    index.get("column_sorting", {}),
                    str(index.get("dialect_options", {}).get("postgresql_where", "")),
                )
                for index in inspector.get_indexes(name, schema=schema)
                if not index.get("duplicates_constraint")
            ),
            "foreign_keys": sorted(foreign_keys, key=lambda foreign_key: foreign_key["name"]),
        }
    return definitions


def assert_migration_model_agreement(connection, migrated_schema):
    # PostgreSQL parses both definitions, normalizing equivalent casts/checks/defaults.
    reference = f"telemetry_model_{uuid4().hex}"
    original_path = connection.scalar(text("SHOW search_path"))
    connection.execute(text(f'CREATE SCHEMA "{reference}"'))
    try:
        connection.execute(text("SELECT set_config('search_path', :schema, true)"), {"schema": reference})
        for table in TABLES:
            table.create(connection)
        expected = telemetry_schema_definition(connection, reference)
        actual = telemetry_schema_definition(connection, migrated_schema)
        assert actual == expected
    finally:
        connection.execute(text("SELECT set_config('search_path', :path, true)"), {"path": original_path})
        connection.execute(text(f'DROP SCHEMA "{reference}" CASCADE'))


def test_migration_upgrade_downgrade_upgrade_business_schema_unchanged(postgres):
    database, _, schema = postgres
    with database.engine.begin() as connection:
        before = schema_snapshot(connection)
        connection.execute(text("INSERT INTO teams(id, name, sport, league) VALUES (1, 'Home', 'NBA', 'NBA'), (2, 'Away', 'NBA', 'NBA')"))
        connection.execute(text("INSERT INTO games(id,sport,league,home_team_id,away_team_id,game_date) VALUES (1,'NBA','NBA',1,2,'2026-10-10')"))
        connection.execute(text("INSERT INTO predictions(id,game_id,model_version,market,selection,npi_score,generation_id,input_fingerprint) VALUES (1,1,'NPI-5.0','spread','HOME',150,:generation,'unverified:manual')"), {"generation": str(uuid4())})
        originals = {
            table: connection.execute(text(f'SELECT row_to_json(t)::text FROM "{table}" t ORDER BY id')).scalars().all()
            for table in before
        }
        command.upgrade(migration_config(connection), "head")
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "e7b4c2d9a610"
        assert schema_snapshot(connection) == before
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) - set(before) == {"alembic_version", *(table.name for table in TABLES)}
        for table in TABLES:
            assert connection.scalar(select(text("count(*)")).select_from(table)) == 0
            actual_columns = {column["name"]: column for column in inspector.get_columns(table.name)}
            assert set(actual_columns) == set(table.columns.keys())
            actual_checks = {check["name"] for check in inspector.get_check_constraints(table.name)}
            assert {constraint.name for constraint in table.constraints if constraint.__class__.__name__ == "CheckConstraint"} == actual_checks
            assert {index.name for index in table.indexes} == {
                index["name"] for index in inspector.get_indexes(table.name) if not index.get("duplicates_constraint")
            }
        assert inspector.get_foreign_keys("worker_cycles")[0]["options"]["ondelete"] == "CASCADE"
        assert inspector.get_foreign_keys("worker_cycle_sources")[0]["options"]["ondelete"] == "CASCADE"
        index = next(index for index in inspector.get_indexes("worker_cycles") if index["name"] == "uq_worker_cycles_running_instance")
        assert index["unique"]
        assert "running" in str(index["dialect_options"]["postgresql_where"])
        assert_migration_model_agreement(connection, schema)
        command.downgrade(migration_config(connection), "c8d2f6a109b4")
        assert not set(inspect(connection).get_table_names()) & {table.name for table in TABLES}
        assert schema_snapshot(connection) == before
        command.upgrade(migration_config(connection), "head")
        assert_migration_model_agreement(connection, schema)
        assert schema_snapshot(connection) == before
        for table, rows in originals.items():
            assert connection.execute(text(f'SELECT row_to_json(t)::text FROM "{table}" t ORDER BY id')).scalars().all() == rows


def test_postgres_constraints_json_uuid_timezone_partial_unique_and_cascade(migrated):
    database, _, _ = migrated
    service = WorkerTelemetryService(database)
    instance = register(service)
    register(service)
    identifier, ids = cycle(service, instance)
    with database.transaction() as session:
        row = session.execute(select(WorkerInstance.__table__).where(WorkerInstance.id == instance)).mappings().one()
        assert row["started_at"].tzinfo is not None
        assert row["started_at"].utcoffset() == timedelta(0)
        assert row["id"] == instance
        assert session.scalar(select(WorkerCycleSource.fetched)) is None
    for values in ({"source_manifest": {}}, {"state": "invalid"}, {"progress_at": NOW - timedelta(seconds=1)}):
        with pytest.raises(IntegrityError), database.engine.begin() as connection:
            connection.execute(update(WorkerInstance.__table__).where(WorkerInstance.id == instance).values(**values))
    with pytest.raises(IntegrityError), database.engine.begin() as connection:
        connection.execute(insert(WorkerCycle.__table__).values(
            id=uuid4(), instance_id=instance, sequence=2, state="running", started_at=NOW, expected_sources=1,
        ))
    finish(service, identifier, ids)
    with database.engine.begin() as connection:
        connection.execute(text("DELETE FROM worker_instances WHERE id=:id"), {"id": instance})
        assert connection.scalar(select(WorkerCycle.id)) is None
        assert connection.scalar(select(WorkerCycleSource.id)) is None


def test_actual_statement_and_lock_timeouts(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    instance = register(service)
    with database.transaction() as session:
        assert session.scalar(text("SHOW statement_timeout")) == "500ms"
        assert session.scalar(text("SHOW lock_timeout")) == "100ms"
        assert session.scalar(text("SHOW timezone")) == "UTC"
    with pytest.raises(TelemetryError, match="storage_unavailable"):
        with database.transaction() as session:
            session.execute(text("SELECT pg_sleep(1)"))
    blocker = scoped_database(url, schema)
    try:
        with blocker.transaction() as session:
            session.execute(select(WorkerInstance.id).where(WorkerInstance.id == instance).with_for_update())
            with pytest.raises(TelemetryError, match="storage_unavailable"):
                service.update_heartbeat(instance, NOW + timedelta(seconds=1))
    finally:
        blocker.dispose()
    assert service.update_heartbeat(instance, NOW + timedelta(seconds=1))


def test_postgres_connection_and_pool_configuration(postgres):
    database, url, schema = postgres
    other = scoped_database(url, schema)
    captured = {}
    def parameters(_dialect, _record, _args, kwargs):
        captured.update(kwargs)
    event.listen(other.engine, "do_connect", parameters)
    try:
        with other.transaction() as session:
            session.execute(text("SELECT 1"))
        assert captured["connect_timeout"] == 2
        assert captured["options"] == "-c statement_timeout=500 -c lock_timeout=100 -c timezone=UTC"
        assert other.engine.pool.size() == 1
        assert other.engine.pool._max_overflow == 0
        assert other.engine.pool.timeout() == 0.2
    finally:
        other.dispose()


def test_concurrent_begin_and_source_registration_are_idempotent(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    instance = register(service)
    identifier = uuid4()
    barrier = Barrier(2)
    def begin():
        local = scoped_database(url, schema)
        try:
            barrier.wait(timeout=5)
            recorder = WorkerTelemetryService(local)
            sequence = recorder.begin_cycle(instance, identifier, started_at=NOW, expected_sources=1)
            return sequence, recorder.register_sources(identifier, (SOURCE,))
        finally:
            local.dispose()
    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(lambda _: begin(), range(2)))
    assert first == second
    assert first[0] == 1
    with database.transaction() as session:
        assert session.scalar(select(text("count(*)")).select_from(WorkerCycle.__table__)) == 1
        assert session.scalar(select(text("count(*)")).select_from(WorkerCycleSource.__table__)) == 1


def test_concurrent_different_cycles_only_one_can_run(migrated):
    database, url, schema = migrated
    instance = register(WorkerTelemetryService(database))
    barrier = Barrier(2)
    def begin():
        local = scoped_database(url, schema)
        try:
            barrier.wait(timeout=5)
            try:
                return WorkerTelemetryService(local).begin_cycle(instance, uuid4(), started_at=NOW, expected_sources=1)
            except TelemetryError as error:
                return error.code
        finally:
            local.dispose()
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: begin(), range(2)))
    assert outcomes.count(1) == 1
    assert outcomes.count("illegal_transition") == 1


def test_concurrent_source_observations_retain_latest_and_date_bounds(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    identifier, ids = cycle(service, register(service))
    service.transition_source(identifier, ids[0], state="running", at=NOW)
    barrier = Barrier(2)
    def observe(seconds):
        local = scoped_database(url, schema)
        try:
            barrier.wait(timeout=5)
            observed = NOW + timedelta(seconds=seconds)
            return WorkerTelemetryService(local).transition_source(
                identifier, ids[0], state="running", at=observed,
                timestamps={
                    "last_game_processed_at": observed,
                    "latest_odds_observed_at": observed,
                    "latest_prediction_published_at": observed,
                    "game_date_min": observed,
                    "game_date_max": observed,
                },
            )
        finally:
            local.dispose()
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(observe, (20, 10)))
    assert any(outcomes)
    with database.transaction() as session:
        row = session.execute(select(WorkerCycleSource.__table__)).mappings().one()
        for field in ("last_game_processed_at", "latest_odds_observed_at", "latest_prediction_published_at", "game_date_max"):
            assert row[field] == NOW + timedelta(seconds=20)
        assert row["game_date_min"] == NOW + timedelta(seconds=10)
    assert not service.transition_source(
        identifier, ids[0], state="running", at=NOW + timedelta(seconds=20),
        timestamps={"latest_odds_observed_at": NOW + timedelta(seconds=20)},
    )


def test_postgres_finalization_preserves_failure_and_abandonment_duration(migrated):
    database, _, _ = migrated
    service = WorkerTelemetryService(database)
    identifier, ids = cycle(service, register(service))
    service.transition_source(
        identifier, ids[0], state="running", at=NOW,
        counters={"fetched": 5, "errors": 2}, error_code="publication_failed",
    )
    with pytest.raises(TelemetryError, match="conflict"):
        service.transition_source(identifier, ids[0], state="failed", at=NOW, duration_ms=0,
                                  counters={"errors": 0})
    with pytest.raises(TelemetryError, match="incomplete_source"):
        service.transition_source(identifier, ids[0], state="succeeded", at=NOW, duration_ms=0)
    assert service.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=1), at=NOW + timedelta(seconds=2))
    with database.transaction() as session:
        row = session.execute(select(WorkerCycleSource.__table__)).mappings().one()
        assert (row["fetched"], row["errors"], row["error_code"], row["duration_ms"]) == (5, 2, "publication_failed", None)
        assert session.scalar(select(WorkerCycle.duration_ms)) is None


def test_abandonment_race_rechecks_locked_instance(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    instance = register(service, at=NOW - timedelta(hours=2))
    identifier, _ = cycle(service, instance, at=NOW - timedelta(hours=2))
    other = scoped_database(url, schema)
    try:
        # Commit the heartbeat while holding the same row lock abandonment uses.
        with other.transaction() as session:
            session.execute(update(WorkerInstance.__table__).where(WorkerInstance.id == instance).values(heartbeat_at=NOW))
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(service.abandon_cycle, identifier, stale_before=NOW - timedelta(minutes=1), at=NOW)
                session.commit()
                assert pending.result(timeout=5) is False
        with database.transaction() as session:
            assert session.scalar(select(WorkerCycle.state)) == "running"
    finally:
        other.dispose()


@pytest.mark.parametrize("field", SOURCE_LIFECYCLE_TIMESTAMPS)
@pytest.mark.parametrize("seconds_after", [0, 1])
def test_postgres_abandonment_chronology_is_atomic(migrated, field, seconds_after):
    database, _, _ = migrated
    assert_abandonment_chronology(WorkerTelemetryService(database), database, field, seconds_after)


def test_postgres_scheduled_game_dates_are_not_lifecycle_occurrences(migrated):
    database, _, _ = migrated
    assert_scheduled_game_dates_do_not_block_abandonment(WorkerTelemetryService(database))


def test_completion_and_abandonment_race_keeps_terminal_evidence_consistent(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    instance = register(service)
    identifier, ids = cycle(service, instance)
    at = NOW + timedelta(seconds=20)
    service.transition_source(identifier, ids[0], state="running", at=NOW)
    service.transition_source(identifier, ids[0], state="succeeded", at=at, duration_ms=123)
    barrier = Barrier(2)

    def finalize(action):
        local = scoped_database(url, schema)
        try:
            recorder = WorkerTelemetryService(local)
            barrier.wait(timeout=5)
            try:
                if action == "complete":
                    return recorder.complete_cycle(identifier, state="succeeded", finished_at=at, duration_ms=456)
                return recorder.abandon_cycle(identifier, stale_before=NOW + timedelta(seconds=5), at=at)
            except TelemetryError as error:
                assert error.code == "illegal_transition"
                return error.code
        finally:
            local.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(finalize, ("complete", "abandon")))
    assert sum(outcome is True for outcome in outcomes) == 1
    with database.transaction() as session:
        result = session.execute(select(WorkerCycle.__table__).where(WorkerCycle.id == identifier)).mappings().one()
        owner = session.execute(select(WorkerInstance.__table__).where(WorkerInstance.id == instance)).mappings().one()
        source = session.execute(select(WorkerCycleSource.__table__).where(WorkerCycleSource.id == ids[0])).mappings().one()
        assert result["finished_at"] == source["finished_at"] == at
        assert source["state"] == "succeeded"
        assert source["duration_ms"] == 123
        if result["state"] == "succeeded":
            assert (owner["state"], result["duration_ms"], result["telemetry_complete"]) == ("idle", 456, True)
        else:
            assert result["state"] == "abandoned"
            assert (owner["state"], result["duration_ms"], result["telemetry_complete"]) == ("stopped", None, False)


def test_business_commit_survives_telemetry_transaction_failure(migrated):
    database, url, schema = migrated
    business = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with business.begin() as connection:
            connection.execute(text("INSERT INTO teams(id,name,sport,league) VALUES (10,'Independent','NBA','NBA')"))
            with pytest.raises(TelemetryError):
                with database.transaction() as session:
                    session.execute(text("INSERT INTO worker_instances(id) VALUES (:id)"), {"id": uuid4()})
            assert connection.scalar(text("SELECT count(*) FROM teams")) == 1
        with business.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM teams")) == 1
        with database.transaction() as session:
            assert session.scalar(select(WorkerInstance.id)) is None
    finally:
        business.dispose()


def test_retention_500_batch_dry_run_and_advisory_lock(migrated):
    database, url, schema = migrated
    service = WorkerTelemetryService(database)
    old = NOW - timedelta(days=40)
    instance = register(service, at=old)
    with database.engine.begin() as connection:
        connection.execute(insert(WorkerCycle.__table__), [
            dict(id=uuid4(), instance_id=instance, sequence=sequence, state="succeeded",
                 started_at=old, finished_at=old, duration_ms=0, expected_sources=0)
            for sequence in range(1, 502)
        ])
    service.stop_instance(instance, old)
    preview = service.prune_history(at=NOW, dry_run=True)
    assert (preview.cycles, preview.instances) == (500, 0)
    with database.transaction() as session:
        assert session.scalar(select(text("count(*)")).select_from(WorkerCycle.__table__)) == 501
    blocker = scoped_database(url, schema)
    try:
        with blocker.transaction() as session:
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": CLEANUP_LOCK})
            assert not service.prune_history(at=NOW).lock_acquired
        first = service.prune_history(at=NOW)
        assert (first.cycles, first.instances) == (500, 0)
        second = service.prune_history(at=NOW)
        assert (second.cycles, second.instances) == (1, 1)
    finally:
        blocker.dispose()


def test_retention_instance_batch_and_fresh_instance_exclusion(migrated):
    database, _, _ = migrated
    old = NOW - timedelta(days=40)
    with database.engine.begin() as connection:
        connection.execute(insert(WorkerInstance.__table__), [
            dict(id=uuid4(), worker_name="upcoming-game-worker", state="stopped",
                 started_at=old, heartbeat_at=old, progress_at=old, stopped_at=old,
                 poll_seconds=3600, heartbeat_seconds=60, schedule_mode="after_completion",
                 source_manifest=[])
            for _ in range(501)
        ])
    service = WorkerTelemetryService(database)
    fresh = register(service)
    assert service.prune_history(at=NOW).instances == 500
    assert service.prune_history(at=NOW).instances == 1
    with database.transaction() as session:
        assert session.scalars(select(WorkerInstance.id)).all() == [fresh]
