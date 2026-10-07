from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4
from threading import Lock

import pytest
from sqlalchemy import event as sql_event, select, update

from app.database.telemetry_session import TelemetryConfig, TelemetryDatabase, TelemetryError
from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import WorkerCycleSource
from app.models.worker_instance import WorkerInstance
from app.services.worker_telemetry_service import SourceIdentity, WorkerTelemetryService
from app.workers import final_score_worker, upcoming_game_worker
from app.workers.worker_instrumentation import WorkerInstrumentation
from test_nba_preseason_sync import db as business_db, event, final, importer, prediction_engine
from test_worker_telemetry import database, block_http


class FakeLease:
    def __init__(self, ownership, identifier):
        self.ownership = ownership
        self.identifier = identifier
        self.closed = False

    def check(self):
        if self.closed:
            raise TelemetryError("ownership_unavailable")

    def close(self, deadline=None, *, discard=False):
        with self.ownership.lock:
            self.ownership.held.discard(self.identifier)
        self.closed = True


class FakeOwnership:
    supported = True

    def __init__(self, database):
        if not hasattr(database, "_test_ownership"):
            database._test_ownership = (set(), Lock())
        self.held, self.lock = database._test_ownership

    def acquire(self, identifier, *, on_unwind=None):
        with self.lock:
            if identifier in self.held:
                return None
            self.held.add(identifier)
        return FakeLease(self, identifier)

    def dispose(self):
        pass


def recorder(database, *, final_score=False, sports=("NBA",)):
    result = WorkerInstrumentation(
        "final-score-worker" if final_score else "upcoming-game-worker", sports, 900,
        "start_to_start" if final_score else "after_completion", database=database,
    )
    if result.enabled and database.engine.dialect.name == "sqlite":
        result.ownership = FakeOwnership(database)
        abandon = result.service.abandon_cycle
        def fake_recovery(*args, recovery_owner=None, **kwargs):
            if recovery_owner is None:
                return abandon(*args, **kwargs)
            lease = result.ownership.acquire(recovery_owner)
            if lease is None:
                return False
            try:
                return abandon(*args, **kwargs)
            finally:
                lease.close()
        result.service.abandon_cycle = fake_recovery
    return result


def records(database, model):
    with database.transaction() as session:
        return session.execute(select(model.__table__).order_by(model.id)).mappings().all()


@pytest.mark.parametrize("identifier", ["not-a-uuid", "", None, object(), "x" * 10000])
def test_invalid_ownership_ids_fail_before_resources(database, monkeypatch, identifier):
    from app.database.worker_ownership import WorkerOwnership, ownership_key
    ownership = WorkerOwnership(database)
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid ownership input accessed an engine or connection")
    monkeypatch.setattr(TelemetryDatabase, "engine", property(forbidden))
    monkeypatch.setattr("app.database.worker_ownership.create_engine", forbidden)
    for operation in (ownership_key, ownership.acquire):
        with pytest.raises(TelemetryError) as caught:
            operation(identifier)
        assert caught.value.code == "invalid_input"
        assert str(caught.value) == "Telemetry operation failed: invalid_input"
    assert ownership._engine is None


def test_canonical_ownership_uuid_normalization():
    from app.database.worker_ownership import ownership_key
    identifier = uuid4()
    assert ownership_key(identifier) == ownership_key(str(identifier)) == ownership_key(str(identifier).upper())


def test_transactional_recovery_fails_closed_on_sqlite(database):
    with pytest.raises(TelemetryError) as caught:
        WorkerTelemetryService(database).abandon_cycle(
            uuid4(), recovery_owner=uuid4(), stale_before=datetime.now(UTC), at=datetime.now(UTC),
        )
    assert caught.value.code == "unsupported_database"


@pytest.mark.parametrize("boundary", ["registration", "registered", "recovery"])
@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, TelemetryError])
def test_startup_unwind_preserves_exception_and_shared_deadline(database, monkeypatch, boundary, error_type):
    telemetry = recorder(database)
    error = error_type(23 if error_type is SystemExit else "storage_unavailable")
    register = telemetry.service.register_instance
    leases = []
    acquire = telemetry.ownership.acquire
    def own(*args, **kwargs):
        lease = acquire(*args, **kwargs)
        leases.append(lease)
        return lease
    monkeypatch.setattr(telemetry.ownership, "acquire", own)
    def fail(*args, **kwargs):
        if boundary == "registered":
            register(*args, **kwargs)
        raise error
    monkeypatch.setattr(
        telemetry if boundary == "recovery" else telemetry.service,
        "recover_stale_cycles" if boundary == "recovery" else "register_instance", fail,
    )
    if error_type is TelemetryError and boundary != "recovery":
        with telemetry.process():
            assert not telemetry.enabled
    else:
        with pytest.raises(error_type) as caught:
            with telemetry.process():
                pytest.fail("Startup interruption entered business work")
        assert caught.value is error
    assert telemetry._cleanup_deadline is not None
    assert leases[0].closed and telemetry._lease is None
    assert not any(row["state"] == "stopped" for row in records(database, WorkerInstance))
    contender = acquire(telemetry.instance_id)
    assert contender is not None
    contender.close()


def wire_upcoming(monkeypatch, business_db, rows, *, sports=("NBA",)):
    services = []
    fetches = []
    def create(**_kwargs):
        service = importer(business_db, rows)
        services.append(service)
        fetches.append(service.live_data.fetch_games)
        return service
    monkeypatch.setattr(upcoming_game_worker, "_configured_sports", lambda: sports)
    monkeypatch.setattr(upcoming_game_worker, "SessionLocal", lambda: business_db)
    monkeypatch.setattr(upcoming_game_worker, "GameOddsImporter", create)
    monkeypatch.setattr(upcoming_game_worker, "PredictionEngine", prediction_engine)
    monkeypatch.setattr(upcoming_game_worker, "collect_ncaaf_shadow_evidence", lambda: None)
    return services, fetches


def wire_final(monkeypatch, business_db, rows, *, sports=("NBA",), failure=None):
    provider = MagicMock()
    def fetch(key, **_kwargs):
        if failure and key == failure:
            raise RuntimeError("secret-provider-payload")
        return rows.get(key, [])
    provider.get_scores.side_effect = fetch
    monkeypatch.setattr(final_score_worker, "_configured_sports", lambda: sports)
    monkeypatch.setattr(final_score_worker, "SessionLocal", lambda: business_db)
    monkeypatch.setattr(final_score_worker, "OddsProviderClient", lambda: provider)
    monkeypatch.setattr(final_score_worker, "settle_ncaaf_shadow_evidence", lambda: None)
    return provider


@pytest.mark.parametrize("final_score", [False, True])
def test_disabled_workers_create_no_engine_or_session_and_need_no_storage_configuration(
    monkeypatch, business_db, final_score, caplog,
):
    database = TelemetryDatabase(config=TelemetryConfig())
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Disabled telemetry initialized storage")
    monkeypatch.setattr("app.database.telemetry_session.create_engine", forbidden)
    monkeypatch.setattr(database, "transaction", forbidden)
    monkeypatch.setattr("app.database.telemetry_session._settings", forbidden)
    monkeypatch.setattr("app.database.worker_ownership.WorkerOwnership.acquire", forbidden)
    wire_upcoming(monkeypatch, business_db, {})
    provider = wire_final(monkeypatch, business_db, {})
    with caplog.at_level("INFO"), recorder(database, final_score=final_score).process():
        result = (final_score_worker if final_score else upcoming_game_worker).run_once()["NBA"]
    assert result["errors" if final_score else "prediction_errors"] == 0
    assert not any("Worker telemetry" in record.message for record in caplog.records)
    assert database._engine is None
    if final_score:
        assert [call.args[0] for call in provider.get_scores.call_args_list] == [
            "basketball_nba", "basketball_nba_preseason",
        ]
    else:
        assert result["imported"] == 0


def test_upcoming_real_business_idempotency_source_identity_and_sequence(database, business_db, monkeypatch):
    services, fetches = wire_upcoming(monkeypatch, business_db, {
        "basketball_nba": [event("regular")],
        "basketball_nba_preseason": [event("preseason")],
    })
    commits = []
    sql_event.listen(business_db, "after_commit", lambda _session: commits.append(True))
    baseline = upcoming_game_worker.run_once()
    baseline_commits = len(commits)
    baseline_predictions = [row.id for row in business_db.query(Prediction)]
    with recorder(database).process() as telemetry:
        first = upcoming_game_worker.run_once()
        refresh_commits = len(commits) - baseline_commits
        second = upcoming_game_worker.run_once()
        assert len(commits) - baseline_commits == 2 * refresh_commits
        assert telemetry.enabled
    assert first == second == baseline
    assert business_db.query(Game).count() == 2
    assert business_db.query(Odds).count() == 6
    assert [row.id for row in business_db.query(Prediction)] == baseline_predictions
    assert all(service.live_data.fetch_games is fetch for service, fetch in zip(services, fetches))
    assert all(fetch.call_count == 2 for fetch in fetches)
    cycles = sorted(records(database, WorkerCycle), key=lambda row: row["sequence"])
    assert [row["sequence"] for row in cycles] == [1, 2]
    assert all(row["state"] == "succeeded" and row["telemetry_complete"] for row in cycles)
    sources = records(database, WorkerCycleSource)
    assert {(row["sport"], row["league"], row["provider_source"]) for row in sources} == {
        ("NBA", "NBA", "basketball_nba"), ("NBA", "NBA_PRESEASON", "basketball_nba_preseason"),
    }
    for row in sources:
        assert row["fetched"] == row["processed"] == row["refreshed"] == row["usable_odds"] == 1
        assert row["created"] == row["errors"] == 0
        assert row["prediction_rows_returned"] == 3
        assert row["publications_created"] is row["publications_reused"] is row["prediction_rows_created"] is None
        assert row["latest_prediction_published_at"] is row["latest_odds_observed_at"] is None
        assert row["last_game_processed_at"] is not None
        assert row["game_date_min"] == row["game_date_max"]
    instance = records(database, WorkerInstance)[0]
    assert instance["state"] == "stopped"
    assert instance["last_cycle_outcome"] == "succeeded"
    assert instance["stopped_at"] >= instance["heartbeat_at"] >= instance["started_at"]


@pytest.mark.parametrize("failure", ["basketball_nba", "basketball_nba_preseason", "both"])
def test_upcoming_provider_failure_retains_unknown_counts_and_other_sources(
    database, business_db, monkeypatch, failure,
):
    services, fetches = wire_upcoming(monkeypatch, business_db, {})
    original_factory = upcoming_game_worker.GameOddsImporter
    def create(**kwargs):
        service = original_factory(**kwargs)
        def fetch(key):
            if failure in {key, "both"}:
                raise RuntimeError("secret-provider-payload")
            return []
        fetches[-1].side_effect = fetch
        return service
    monkeypatch.setattr(upcoming_game_worker, "GameOddsImporter", create)
    with recorder(database).process() as telemetry:
        result = upcoming_game_worker.run_once()["NBA"]
        assert telemetry.enabled
    assert result["imported"] == result["predictions_generated"] == 0
    sources = records(database, WorkerCycleSource)
    for row in sources:
        if failure in {row["provider_source"], "both"}:
            assert row["state"] == "failed"
            assert row["errors"] == 1 and row["error_code"] == "provider_unavailable"
            assert row["fetched"] is row["processed"] is row["prediction_rows_returned"] is None
        else:
            assert row["state"] == "succeeded" and row["fetched"] == 0
    cycle = records(database, WorkerCycle)[0]
    assert cycle["state"] == ("failed" if failure == "both" else "partial")
    assert cycle["telemetry_complete"]
    assert fetches[0].call_count == 2


def test_final_real_settlement_counters_and_idempotency(database, business_db, monkeypatch):
    rows = {"basketball_nba": [event("regular")], "basketball_nba_preseason": [event("preseason")]}
    imported = importer(business_db, rows).import_games("NBA")
    engine = prediction_engine()
    for game in imported:
        engine.analyze_markets(business_db, game.id)
    provider = wire_final(monkeypatch, business_db, {key: [final(row) for row in value] for key, value in rows.items()})
    commits = []
    sql_event.listen(business_db, "after_commit", lambda _session: commits.append(True))
    baseline = final_score_worker.run_once()
    ids = [row.id for row in business_db.query(PredictionResult)]
    commits.clear()
    disabled_repeat = final_score_worker.run_once()
    disabled_commits = len(commits)
    commits.clear()
    with recorder(database, final_score=True).process() as telemetry:
        observed_repeat = final_score_worker.run_once()
        assert telemetry.enabled
    assert observed_repeat == disabled_repeat
    assert baseline["NBA"]["finalized"] == 2 and baseline["NBA"]["settled"] == 2
    assert observed_repeat["NBA"]["already_final"] == 2
    assert len(commits) == disabled_commits
    assert [row.id for row in business_db.query(PredictionResult)] == ids
    assert provider.get_scores.call_count == 6
    for source in records(database, WorkerCycleSource):
        assert source["fetched"] == source["matched"] == source["already_final"] == 1
        assert source["games_settled"] == 0
        assert source["finalized"] == source["errors"] == 0
        assert source["prediction_results_created"] is None
        assert source["last_game_processed_at"] is not None
        assert source["game_date_min"] is source["game_date_max"] is None
    assert records(database, WorkerCycle)[0]["state"] == "succeeded"


@pytest.mark.parametrize("failure", ["basketball_nba", "basketball_nba_preseason"])
def test_final_failed_source_does_not_hide_success(database, business_db, monkeypatch, failure):
    provider = wire_final(monkeypatch, business_db, {}, failure=failure)
    with recorder(database, final_score=True).process() as telemetry:
        result = final_score_worker.run_once()["NBA"]
        assert telemetry.enabled
    assert result["errors"] == 1 and provider.get_scores.call_count == 2
    sources = records(database, WorkerCycleSource)
    for row in sources:
        assert row["state"] == ("failed" if row["provider_source"] == failure else "succeeded")
    assert records(database, WorkerCycle)[0]["state"] == "partial"


@pytest.mark.parametrize("final_score", [False, True])
@pytest.mark.parametrize("boundary", [
    "register_instance", "begin_cycle", "register_sources", "source_update",
    "source_finish", "complete_cycle", "update_heartbeat", "update_progress",
    "stop_instance", "recovery",
])
def test_telemetry_failures_do_not_change_business_calls_or_commits(
    database, business_db, monkeypatch, caplog, final_score, boundary,
):
    services, fetches = wire_upcoming(monkeypatch, business_db, {})
    provider = wire_final(monkeypatch, business_db, {})
    worker = final_score_worker if final_score else upcoming_game_worker
    baseline = worker.run_once()
    telemetry = recorder(database, final_score=final_score)
    attempted = []
    def failure(*args, **kwargs):
        attempted.append(True)
        raise TelemetryError("credential-bearing-url-must-not-be-logged")
    if boundary in {"source_update", "source_finish"}:
        original = telemetry.service.transition_source
        def transition(*args, **kwargs):
            if (boundary == "source_update" and "counters" in kwargs) or (
                boundary == "source_finish" and kwargs["state"] != "running"
            ):
                return failure()
            return original(*args, **kwargs)
        monkeypatch.setattr(telemetry.service, "transition_source", transition)
    elif boundary == "recovery":
        original_transaction = database.transaction
        calls = 0
        def transaction():
            nonlocal calls
            calls += 1
            if calls == 2:
                return failure()
            return original_transaction()
        monkeypatch.setattr(database, "transaction", transaction)
    else:
        monkeypatch.setattr(telemetry.service, boundary, failure)
    commits = []
    rollbacks = []
    sql_event.listen(business_db, "after_commit", lambda _session: commits.append(True))
    sql_event.listen(business_db, "after_rollback", lambda _session: rollbacks.append(True))
    with caplog.at_level("WARNING"), telemetry.process():
        assert worker.run_once() == baseline
        assert worker.run_once() == baseline
    assert attempted == [True]
    assert not commits and not rollbacks
    assert not telemetry.enabled
    warnings = [record.message for record in caplog.records if "Worker telemetry unavailable" in record.message]
    assert len(warnings) == 1
    assert "credential" not in warnings[0]
    if final_score:
        assert provider.get_scores.call_count == 6
    else:
        assert all(fetch.call_count == 2 for fetch in fetches)


@pytest.mark.parametrize("final_score", [False, True])
def test_telemetry_writes_only_after_business_session_close(database, business_db, monkeypatch, final_score):
    wire_upcoming(monkeypatch, business_db, {"basketball_nba": [event("close-boundary")]})
    wire_final(monkeypatch, business_db, {})
    active = False
    original_close = business_db.close
    def session():
        nonlocal active
        active = True
        return business_db
    def close():
        nonlocal active
        original_close()
        active = False
    monkeypatch.setattr(business_db, "close", close)
    worker = final_score_worker if final_score else upcoming_game_worker
    monkeypatch.setattr(worker, "SessionLocal", session)
    def check(_connection, _cursor, _statement, _parameters, _context, _executemany):
        assert not active, "Telemetry SQL overlapped a live business session"
    sql_event.listen(database.engine, "before_cursor_execute", check)
    with recorder(database, final_score=final_score).process() as telemetry:
        worker.run_once()
        assert telemetry.enabled


@pytest.mark.parametrize("final_score", [False, True])
def test_failed_business_session_close_suppresses_storage_and_preserves_original_exception(
    database, business_db, monkeypatch, final_score,
):
    wire_upcoming(monkeypatch, business_db, {})
    wire_final(monkeypatch, business_db, {})
    original = RuntimeError("original session close failure")
    active = False
    def session():
        nonlocal active
        active = True
        return business_db
    def fail_close():
        raise original
    worker = final_score_worker if final_score else upcoming_game_worker
    monkeypatch.setattr(worker, "SessionLocal", session)
    def check(*_args):
        assert not active, "Telemetry storage ran after failed business close"
    sql_event.listen(database.engine, "before_cursor_execute", check)
    with monkeypatch.context() as close_patch:
        close_patch.setattr(business_db, "close", fail_close)
        with pytest.raises(RuntimeError) as caught:
            with recorder(database, final_score=final_score).process() as telemetry:
                worker.run_once()
    assert caught.value is original and not telemetry.enabled


@pytest.mark.parametrize("final_score", [False, True])
def test_keyboard_interrupt_preserves_exception_and_leaves_incomplete_evidence(
    database, business_db, monkeypatch, final_score,
):
    services, _fetches = wire_upcoming(monkeypatch, business_db, {})
    provider = wire_final(monkeypatch, business_db, {})
    original_factory = upcoming_game_worker.GameOddsImporter
    interruption = KeyboardInterrupt("original interrupt")
    if final_score:
        provider.get_scores.side_effect = interruption
    else:
        def create(**kwargs):
            service = original_factory(**kwargs)
            service.live_data.fetch_games.side_effect = interruption
            return service
        monkeypatch.setattr(upcoming_game_worker, "GameOddsImporter", create)
    with pytest.raises(KeyboardInterrupt) as caught:
        with recorder(database, final_score=final_score).process():
            (final_score_worker if final_score else upcoming_game_worker).run_once()
    assert caught.value is interruption
    cycle = records(database, WorkerCycle)[0]
    assert cycle["state"] == "failed" and not cycle["telemetry_complete"]
    assert cycle["error_code"] == "worker_stopped"
    for source in records(database, WorkerCycleSource):
        assert source["state"] == "missing" and source["duration_ms"] is None
    assert records(database, WorkerInstance)[0]["state"] == "stopped"


def test_recovery_abandons_only_stale_cycles_and_preserves_unknown_durations(database):
    service = WorkerTelemetryService(database)
    source = SourceIdentity("NBA", "NBA", "odds_api", "basketball_nba")
    now = datetime.now(UTC)
    stale_cycle, healthy_cycle = uuid4(), uuid4()
    for identifier, at in ((stale_cycle, now - timedelta(days=1)), (healthy_cycle, now)):
        instance = uuid4()
        service.register_instance(
            instance, worker_name="upcoming-game-worker", started_at=at, poll_seconds=900,
            heartbeat_seconds=900, schedule_mode="after_completion", sources=(source,),
        )
        service.begin_cycle(instance, identifier, started_at=at, expected_sources=1)
        ids = service.register_sources(identifier, (source,))
        service.transition_source(identifier, ids[0], state="running", at=at, counters={"fetched": 5, "errors": 2}, error_code="publication_failed")
    with recorder(database).process() as telemetry:
        assert telemetry.enabled
    cycles = {row["id"]: row for row in records(database, WorkerCycle)}
    assert cycles[stale_cycle]["state"] == "abandoned" and cycles[stale_cycle]["duration_ms"] is None
    assert cycles[healthy_cycle]["state"] == "running"
    sources = {row["cycle_id"]: row for row in records(database, WorkerCycleSource)}
    assert sources[stale_cycle]["state"] == "missing" and sources[stale_cycle]["duration_ms"] is None
    assert sources[stale_cycle]["fetched"] == 5 and sources[stale_cycle]["errors"] == 2
    assert sources[stale_cycle]["error_code"] == "publication_failed"


@pytest.mark.parametrize("final_score", [False, True])
def test_sleep_contract_and_original_exit_are_preserved(database, business_db, monkeypatch, final_score):
    worker = final_score_worker if final_score else upcoming_game_worker
    wire_upcoming(monkeypatch, business_db, {})
    wire_final(monkeypatch, business_db, {})
    monkeypatch.setattr(worker, "WorkerInstrumentation", lambda *args: recorder(database, final_score=final_score))
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        raise KeyboardInterrupt
    monkeypatch.setattr(worker.time, "sleep", sleep)
    with pytest.raises(KeyboardInterrupt):
        worker.run_forever()
    assert len(sleeps) == 1
    poll = worker._poll_seconds()
    assert sleeps[0] == poll if not final_score else 1 <= sleeps[0] <= poll
    assert records(database, WorkerInstance)[0]["state"] == "stopped"
    assert records(database, WorkerCycle)[0]["state"] == "succeeded"


def test_original_business_exception_survives_failed_cleanup(database, monkeypatch):
    telemetry = recorder(database)
    original = RuntimeError("original business traceback")
    def fail(*_args, **_kwargs):
        raise TelemetryError("storage_unavailable")
    with pytest.raises(RuntimeError) as caught:
        with telemetry.process(), telemetry.cycle():
            monkeypatch.setattr(telemetry.service, "complete_cycle", fail)
            raise original
    assert caught.value is original
    assert not telemetry.enabled


def test_unexpected_prediction_setup_failure_cannot_report_source_or_cycle_success(
    database, business_db, monkeypatch,
):
    wire_upcoming(monkeypatch, business_db, {"basketball_nba": [event("engine-failure")]})
    def fail():
        raise RuntimeError("original engine setup failure")
    monkeypatch.setattr(upcoming_game_worker, "PredictionEngine", fail)
    with recorder(database).process() as telemetry:
        result = upcoming_game_worker.run_once()
        assert telemetry.enabled
    assert result["NBA"]["imported"] == 1
    cycle = records(database, WorkerCycle)[0]
    assert cycle["state"] == "failed" and not cycle["telemetry_complete"]
    assert all(source["state"] == "missing" for source in records(database, WorkerCycleSource))
    assert all(source["prediction_rows_returned"] is None for source in records(database, WorkerCycleSource))


@pytest.mark.parametrize("final_score", [False, True])
@pytest.mark.parametrize("boundary", ["source_update", "source_finish", "complete_cycle", "stop_instance"])
def test_failure_during_real_business_writes_preserves_commits_and_idempotency(
    database, business_db, monkeypatch, final_score, boundary,
):
    rows = {"basketball_nba": [event("real-business")]}
    wire_upcoming(monkeypatch, business_db, rows)
    wire_final(monkeypatch, business_db, {"basketball_nba": [final(rows["basketball_nba"][0])]})
    upcoming_game_worker.run_once()
    worker = final_score_worker if final_score else upcoming_game_worker
    worker.run_once()
    commits = []
    rollbacks = []
    sql_event.listen(business_db, "after_commit", lambda _session: commits.append(True))
    sql_event.listen(business_db, "after_rollback", lambda _session: rollbacks.append(True))
    baseline = worker.run_once()
    expected_commits = len(commits)
    expected_rollbacks = len(rollbacks)
    ids = [row.id for row in business_db.query(Prediction)]
    result_ids = [row.id for row in business_db.query(PredictionResult)]
    commits.clear()
    rollbacks.clear()
    telemetry = recorder(database, final_score=final_score)
    def fail(*_args, **_kwargs):
        raise TelemetryError("storage_unavailable")
    if boundary.startswith("source_"):
        original = telemetry.service.transition_source
        def transition(*args, **kwargs):
            if (boundary == "source_update" and "counters" in kwargs) or (
                boundary == "source_finish" and kwargs["state"] != "running"
            ):
                return fail()
            return original(*args, **kwargs)
        monkeypatch.setattr(telemetry.service, "transition_source", transition)
    else:
        monkeypatch.setattr(telemetry.service, boundary, fail)
    with telemetry.process():
        assert worker.run_once() == baseline
    assert not telemetry.enabled
    assert len(commits) == expected_commits and len(rollbacks) == expected_rollbacks
    assert [row.id for row in business_db.query(Prediction)] == ids
    assert [row.id for row in business_db.query(PredictionResult)] == result_ids


@pytest.mark.parametrize("final_score", [False, True])
def test_shadow_hook_failure_is_auxiliary_and_keeps_business_results(
    database, business_db, monkeypatch, final_score,
):
    wire_upcoming(monkeypatch, business_db, {}, sports=("NCAAF",))
    wire_final(monkeypatch, business_db, {}, sports=("NCAAF",))
    worker = final_score_worker if final_score else upcoming_game_worker
    hook = "settle_ncaaf_shadow_evidence" if final_score else "collect_ncaaf_shadow_evidence"
    monkeypatch.setattr(worker, hook, MagicMock(side_effect=RuntimeError("shadow exception")))
    with recorder(database, final_score=final_score, sports=("NCAAF",)).process():
        result = worker.run_once()["NCAAF"]
    assert result["errors" if final_score else "prediction_errors"] == 0
    cycle = records(database, WorkerCycle)[0]
    assert cycle["state"] == "partial" and cycle["auxiliary_errors"] == 1
    assert cycle["telemetry_complete"]


def test_shutdown_cleanup_has_a_budget_and_does_not_report_success(database, monkeypatch):
    telemetry = recorder(database)
    telemetry.register()
    telemetry.start_cycle()
    telemetry._cleanup_deadline = 1
    monkeypatch.setattr("app.workers.worker_instrumentation.time.monotonic", lambda: 10)
    telemetry.finish_cycle(interrupted=True)
    assert not telemetry.enabled
    assert records(database, WorkerCycle)[0]["state"] == "running"


@pytest.mark.parametrize("final_score", [False, True])
def test_missing_telemetry_tables_do_not_block_real_business(
    tmp_path, business_db, monkeypatch, caplog, final_score,
):
    missing = TelemetryDatabase(f"sqlite:///{tmp_path / 'missing.sqlite'}", TelemetryConfig(enabled=True))
    wire_upcoming(monkeypatch, business_db, {"basketball_nba": [event("missing-storage")]})
    wire_final(monkeypatch, business_db, {})
    worker = final_score_worker if final_score else upcoming_game_worker
    baseline = worker.run_once()
    try:
        with recorder(missing, final_score=final_score).process() as telemetry:
            result = worker.run_once()
        assert result == baseline
        assert not telemetry.enabled
        warnings = [record for record in caplog.records if "Worker telemetry unavailable" in record.message]
        assert len(warnings) == 1
        assert "sqlite" not in warnings[0].message
    finally:
        missing.dispose()


@pytest.mark.parametrize("final_score", [False, True])
def test_configuration_failure_is_sanitized_and_does_not_block_business(
    business_db, monkeypatch, final_score,
):
    class Misconfigured(TelemetryDatabase):
        @property
        def config(self):
            raise TelemetryError("invalid_configuration")
    wire_upcoming(monkeypatch, business_db, {})
    wire_final(monkeypatch, business_db, {})
    with recorder(Misconfigured(), final_score=final_score).process() as telemetry:
        result = (final_score_worker if final_score else upcoming_game_worker).run_once()["NBA"]
    assert not telemetry.enabled
    assert result["errors" if final_score else "prediction_errors"] == 0


@pytest.mark.parametrize("sports", [("NBA", "NBA"), ("INVALID SPORT",)])
def test_invalid_manifest_degrades_without_interfering_with_business_configuration(database, sports, caplog):
    telemetry = recorder(database, sports=sports)
    assert not telemetry.enabled
    assert records(database, WorkerInstance) == []
    assert len([record for record in caplog.records if "Worker telemetry unavailable" in record.message]) == 1


def test_unsupported_ownership_disables_cross_instance_recovery(database):
    service = WorkerTelemetryService(database)
    identifier, cycle_id = uuid4(), uuid4()
    at = datetime.now(UTC) - timedelta(days=1)
    source = SourceIdentity("NBA", "NBA", "odds_api", "basketball_nba")
    service.register_instance(
        identifier, worker_name="upcoming-game-worker", started_at=at, poll_seconds=900,
        heartbeat_seconds=900, schedule_mode="after_completion", sources=(source,),
    )
    service.begin_cycle(identifier, cycle_id, started_at=at, expected_sources=1)
    service.register_sources(cycle_id, (source,))
    with WorkerInstrumentation(
        "upcoming-game-worker", ("NBA",), 900, "after_completion", database=database,
    ).process():
        pass
    assert records(database, WorkerCycle)[0]["state"] == "running"


def test_healthy_long_sport_keeps_owned_cycle_and_can_complete(database, business_db, monkeypatch):
    origin = datetime.now(UTC)
    now = [origin]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now[0]
    monkeypatch.setattr("app.workers.worker_instrumentation.datetime", Clock)
    first = recorder(database)
    successor = recorder(database)
    wire_upcoming(monkeypatch, business_db, {
        "basketball_nba": [event(f"healthy-{index}") for index in range(40)],
    })
    engine = prediction_engine()
    analyze = engine.analyze_markets
    processed = []
    def observed(*args, **kwargs):
        rows = analyze(*args, **kwargs)
        processed.append(True)
        now[0] = origin + timedelta(seconds=50 * len(processed))
        if len(processed) == 40:
            before = records(database, WorkerCycleSource)
            successor.register()
            assert records(database, WorkerCycleSource) == before
            assert records(database, WorkerCycle)[0]["state"] == "running"
            owner = next(row for row in records(database, WorkerInstance) if row["id"] == first.instance_id)
            assert owner["state"] == "running"
            assert successor.ownership.acquire(first.instance_id) is None
        return rows
    monkeypatch.setattr(engine, "analyze_markets", observed)
    monkeypatch.setattr(upcoming_game_worker, "PredictionEngine", lambda: engine)
    try:
        with first.process():
            result = upcoming_game_worker.run_once()["NBA"]
            assert first.enabled
        assert result["predictions_generated"] == 120 and result["prediction_errors"] == 0
        assert records(database, WorkerCycle)[0]["state"] == "succeeded"
    finally:
        successor.shutdown()


@pytest.mark.parametrize("final_score", [False, True])
@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
def test_full_unwind_shares_deadline_before_first_source_write(
    database, business_db, monkeypatch, final_score, exception_type,
):
    services, _ = wire_upcoming(monkeypatch, business_db, {})
    provider = wire_final(monkeypatch, business_db, {})
    original = exception_type(17)
    def fetch(key, **kwargs):
        if key == "basketball_nba_preseason":
            raise original
        return []
    if final_score:
        provider.get_scores.side_effect = fetch
    else:
        factory = upcoming_game_worker.GameOddsImporter
        def create(**kwargs):
            service = factory(**kwargs)
            service.live_data.fetch_games.side_effect = fetch
            return service
        monkeypatch.setattr(upcoming_game_worker, "GameOddsImporter", create)
    telemetry = recorder(database, final_score=final_score)
    simulated = [0.0]
    monkeypatch.setattr("app.workers.worker_instrumentation.time.monotonic", lambda: simulated[0])
    calls, releases = [], []
    with pytest.raises(exception_type) as caught:
        with telemetry.process():
            lease = telemetry._lease
            close = lease.close
            def released(deadline=None, *, discard=False):
                releases.append((deadline, simulated[0], discard))
                return close(deadline, discard=discard)
            monkeypatch.setattr(lease, "close", released)
            for name in ("transition_source", "update_heartbeat", "update_progress", "complete_cycle", "stop_instance"):
                operation = getattr(telemetry.service, name)
                def slow(*args, _operation=operation, _name=name, **kwargs):
                    if _name == "transition_source" or telemetry._cleanup_deadline is not None:
                        assert telemetry._cleanup_deadline == 3.0
                        assert simulated[0] < telemetry._cleanup_deadline
                        calls.append((_name, telemetry._cleanup_deadline))
                        simulated[0] += 0.8
                    return _operation(*args, **kwargs)
                monkeypatch.setattr(telemetry.service, name, slow)
            (final_score_worker if final_score else upcoming_game_worker).run_once()
    assert caught.value is original
    assert len(calls) == 4 and {deadline for _, deadline in calls} == {3.0}
    assert releases == [(3.0, 3.2, True)]
    assert not telemetry.enabled
    assert records(database, WorkerCycle)[0]["state"] == "running"
    assert telemetry._lease is None


@pytest.mark.parametrize("final_score", [False, True])
def test_close_exception_starts_one_deadline_and_preserves_exception(
    database, business_db, monkeypatch, final_score,
):
    wire_upcoming(monkeypatch, business_db, {})
    wire_final(monkeypatch, business_db, {})
    telemetry = recorder(database, final_score=final_score)
    original = RuntimeError("original close failure")
    begin = telemetry.begin_cleanup
    deadlines = []
    def observe():
        begin()
        deadlines.append(telemetry._cleanup_deadline)
    monkeypatch.setattr(telemetry, "begin_cleanup", observe)
    with monkeypatch.context() as patch:
        patch.setattr(business_db, "close", MagicMock(side_effect=original))
        with pytest.raises(RuntimeError) as caught:
            with telemetry.process():
                (final_score_worker if final_score else upcoming_game_worker).run_once()
    assert caught.value is original
    assert deadlines[0] is not None and all(value == deadlines[0] for value in deadlines)


@pytest.mark.parametrize("boundary", ["acquire", "check", "release"])
def test_ownership_failure_keeps_business_results_and_bounded_warning(
    database, business_db, monkeypatch, caplog, boundary,
):
    wire_upcoming(monkeypatch, business_db, {})
    expected = upcoming_game_worker.run_once()
    telemetry = recorder(database)
    def fail(*args, **kwargs):
        raise TelemetryError("private-connection-details")
    if boundary == "acquire":
        monkeypatch.setattr(telemetry.ownership, "acquire", fail)
    with telemetry.process():
        if boundary != "acquire":
            if boundary == "check":
                monkeypatch.setattr(telemetry._lease, "check", fail)
            else:
                close = telemetry._lease.close
                def release(*args, **kwargs):
                    close(*args, **kwargs)
                    return fail()
                monkeypatch.setattr(telemetry._lease, "close", release)
        assert upcoming_game_worker.run_once() == expected
    assert not telemetry.enabled and telemetry._lease is None
    messages = [record.message for record in caplog.records if "Worker telemetry unavailable" in record.message]
    assert len(messages) == 1 and "private" not in messages[0]


@pytest.mark.parametrize("final_score", [False, True])
def test_normal_completion_has_no_interruption_deadline(database, business_db, monkeypatch, final_score):
    wire_upcoming(monkeypatch, business_db, {})
    wire_final(monkeypatch, business_db, {})
    telemetry = recorder(database, final_score=final_score)
    operation = telemetry.service.transition_source
    deadlines = []
    def observe(*args, **kwargs):
        deadlines.append(telemetry._cleanup_deadline)
        return operation(*args, **kwargs)
    monkeypatch.setattr(telemetry.service, "transition_source", observe)
    with telemetry.process():
        (final_score_worker if final_score else upcoming_game_worker).run_once()
        assert telemetry._cleanup_deadline is None
        assert records(database, WorkerCycle)[0]["state"] == "succeeded"
    assert deadlines and all(value is None for value in deadlines)
