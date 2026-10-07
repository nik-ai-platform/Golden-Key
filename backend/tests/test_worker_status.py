from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, insert, select

from app.api.v1.operations import router, status_service
from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.core.roles import UserRole
from app.database.telemetry_session import TelemetryConfig, TelemetryDatabase, TelemetryError
from app.models.worker_cycle import WorkerCycle
from app.models.worker_cycle_source import WorkerCycleSource
from app.models.worker_instance import WorkerInstance
from app.schemas.worker_status import CycleStatus, InstanceStatus, WorkerStatus
from app.services.worker_status_service import WorkerStatusService, classify_worker
from app.services.worker_telemetry_service import SourceIdentity, WorkerTelemetryService


NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)


@pytest.fixture
def database(tmp_path):
    db = TelemetryDatabase(f"sqlite:///{tmp_path / 'status.db'}", TelemetryConfig(enabled=True))
    for table in (WorkerInstance.__table__, WorkerCycle.__table__, WorkerCycleSource.__table__):
        table.create(db.engine)
    yield db
    db.dispose()


def instance(**kwargs):
    values = dict(
        id=uuid4(), state="idle", started_at=NOW - timedelta(hours=1),
        heartbeat_at=NOW, progress_at=NOW, stopped_at=None, poll_seconds=3600,
        heartbeat_seconds=3600, schedule_mode="after_completion",
        last_success_at=NOW, last_success_duration_ms=2000, telemetry_failures=0,
        ownership_held=True,
    )
    return InstanceStatus(**(values | kwargs))


def cycle(**kwargs):
    values = dict(
        id=uuid4(), sequence=1, state="succeeded", started_at=NOW - timedelta(seconds=2),
        finished_at=NOW, duration_ms=2000, expected_sources=0, completed_sources=0,
        failed_sources=0, telemetry_complete=True, error_code=None, auxiliary_errors=0,
    )
    return CycleStatus(**(values | kwargs))


def classify(owner=None, cycles=None, **kwargs):
    owner = instance() if owner is None else owner
    status = WorkerStatus(
        worker_name="upcoming-game-worker", health="unknown", latest_instance=owner,
        recent_instances=[owner], recent_cycles=[cycle()] if cycles is None else cycles, **kwargs,
    )
    classify_worker(status, NOW, 120)
    return status


def test_disabled_does_not_connect(monkeypatch):
    db = TelemetryDatabase("postgresql://invalid", TelemetryConfig(enabled=False))
    monkeypatch.setattr(db, "transaction", lambda: pytest.fail("Disabled status must not open storage"))
    result = WorkerStatusService(db).read(at=NOW)
    assert not result.telemetry_enabled
    assert [w.health for w in result.workers] == ["disabled", "disabled"]


def test_no_evidence_is_unknown(database):
    result = WorkerStatusService(database).read(at=NOW)
    assert all(w.health == "unknown" and w.alerts[0].code == "no_evidence" for w in result.workers)


@pytest.mark.parametrize("poll", [60, 900, 3600])
@pytest.mark.parametrize("excess", [0, 1])
def test_exact_polling_aware_threshold(poll, excess):
    threshold = poll * 2 + 120 + 2
    stale = NOW - timedelta(seconds=threshold + excess)
    status = classify(instance(poll_seconds=poll, heartbeat_at=stale, progress_at=stale))
    assert status.stale_after_seconds == threshold
    assert status.health == ("critical" if excess else "healthy")
    assert {a.code for a in status.alerts} == ({"stale_heartbeat", "stale_progress"} if excess else set())


@pytest.mark.parametrize("state,severity", [("failed", "critical"), ("partial", "warning"), ("abandoned", "critical")])
def test_terminal_alert_classification(state, severity):
    status = classify(cycles=[cycle(state=state, telemetry_complete=False)])
    assert status.health == severity
    assert {a.code for a in status.alerts} == {f"{state}_cycle", "incomplete_coverage"}


def test_running_evidence_does_not_fabricate_failure():
    assert classify(cycles=[cycle(state="running", finished_at=None, telemetry_complete=False), cycle()]).health == "healthy"


def test_unknown_ownership_never_means_healthy():
    assert classify(instance(ownership_held=None)).health == "unknown"


def test_missing_ownership_after_startup_is_critical():
    assert classify(instance(ownership_held=False)).alerts[0].code == "ownership_missing"


def test_startup_grace_and_stopped_state():
    assert classify(instance(state="starting", started_at=NOW, ownership_held=False), cycles=[]).health == "starting"
    assert classify(instance(state="stopped", stopped_at=NOW, ownership_held=False)).health == "stopped"


def test_recent_success_does_not_prove_ownership_during_startup_grace():
    assert classify(instance(started_at=NOW, ownership_held=False)).health == "starting"


def test_competing_owners_are_not_hidden():
    status = WorkerStatus(
        worker_name="upcoming-game-worker", health="unknown", latest_instance=instance(),
        recent_instances=[instance(), instance()], recent_cycles=[cycle()],
    )
    classify_worker(status, NOW, 120)
    assert status.health == "critical"
    assert any(a.code == "competing_owners" for a in status.alerts)


def test_unproven_other_instance_ownership_prevents_healthy_claim():
    latest = instance()
    status = WorkerStatus(
        worker_name="upcoming-game-worker", health="unknown", latest_instance=latest,
        recent_instances=[latest, instance(ownership_held=None)], recent_cycles=[cycle()],
    )
    classify_worker(status, NOW, 120)
    assert status.health == "unknown"


def test_truncated_owner_history_cannot_claim_healthy():
    assert classify(instance_history_truncated=True).health == "warning"


def populate(database, count=1, cycles=1):
    service = WorkerTelemetryService(database)
    source = SourceIdentity("NBA", "NBA_PRESEASON", "odds_api", "basketball_nba_preseason")
    for n in range(count):
        identifier = uuid4()
        at = NOW - timedelta(hours=count - n)
        service.register_instance(
            identifier, worker_name="upcoming-game-worker", started_at=at, poll_seconds=3600,
            heartbeat_seconds=3600, schedule_mode="after_completion", sources=(source,),
        )
        for seq in range(cycles):
            started = at + timedelta(seconds=seq)
            cycle_id = uuid4()
            service.begin_cycle(identifier, cycle_id, started_at=started, expected_sources=1)
            ids = service.register_sources(cycle_id, (source,))
            service.transition_source(cycle_id, ids[0], state="running", at=started)
            service.transition_source(cycle_id, ids[0], state="succeeded", at=started, duration_ms=0, counters={"errors": 0, "fetched": 0})
            service.complete_cycle(cycle_id, state="succeeded", finished_at=started, duration_ms=0)


def test_read_is_bounded_safe_and_does_not_mutate(database):
    populate(database, count=12, cycles=12)
    statements = []
    event.listen(database.engine, "before_cursor_execute", lambda _c, _u, statement, _p, _x, _m: statements.append(statement))
    result = WorkerStatusService(database).read(at=NOW)
    worker = result.workers[1]
    assert len(worker.recent_instances) == len(worker.recent_cycles) == 10
    assert worker.instance_history_truncated and worker.cycle_history_truncated
    assert worker.recent_cycles[0].sequence == 12
    assert worker.latest_instance.started_at.tzinfo == UTC
    source = worker.recent_cycles[0].sources[0]
    assert source.counters["fetched"] == 0
    assert source.counters["prediction_rows_created"] is None
    assert source.started_at.tzinfo == UTC
    assert source.league == "NBA_PRESEASON"
    assert all(s.lstrip().upper().startswith("SELECT") for s in statements)
    payload = result.model_dump_json()
    assert all(value not in payload for value in ("DATABASE_URL", "sqlite:", "client_addr", '"pid"', "source_manifest"))
    assert worker.latest_instance.ownership_held is None
    assert len(worker.recent_cycles[0].sources) == 1


def test_excessive_source_evidence_is_rejected_instead_of_silently_truncated(database):
    populate(database)
    with database.transaction() as session:
        source = dict(session.execute(select(WorkerCycleSource.__table__)).mappings().one())
        session.execute(insert(WorkerCycleSource.__table__), [
            source | {"id": source["id"] + index + 1, "provider_source": f"source_{index}"}
            for index in range(320)
        ])
    with pytest.raises(TelemetryError, match="invalid_evidence"):
        WorkerStatusService(database).read(at=NOW)


@pytest.fixture
def api():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    yield app
    app.dependency_overrides.clear()


def user(role):
    return AuthUser(id=1, username="test", email="test@example.com", role=role, is_active=True)


@pytest.mark.parametrize("role", [UserRole.VIEWER, UserRole.ANALYST])
def test_non_admin_cannot_read_or_invoke_storage(api, role):
    api.dependency_overrides[get_current_user] = lambda: user(role)
    api.dependency_overrides[status_service] = lambda: pytest.fail("Storage dependency accessed for forbidden user")
    assert TestClient(api).get("/api/v1/operations/workers").status_code == 403


def test_missing_auth_rejected_without_storage(api):
    from app.database.session import get_db
    api.dependency_overrides[get_db] = lambda: None
    api.dependency_overrides[status_service] = lambda: pytest.fail("Storage dependency accessed before auth")
    assert TestClient(api).get("/api/v1/operations/workers").status_code == 401


def test_admin_get_and_no_mutating_route(api, database):
    api.dependency_overrides[get_current_user] = lambda: user(UserRole.ADMIN)
    api.dependency_overrides[status_service] = lambda: WorkerStatusService(database)
    client = TestClient(api)
    response = client.get("/api/v1/operations/workers")
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert len(response.json()["workers"]) == 2
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/v1/operations/workers").status_code == 405


def test_storage_errors_are_explicit_and_sanitized(api, caplog):
    api.dependency_overrides[get_current_user] = lambda: user(UserRole.ADMIN)
    def unavailable():
        raise TelemetryError("storage_unavailable")
    api.dependency_overrides[status_service] = lambda: SimpleNamespace(read=unavailable)
    response = TestClient(api).get("/api/v1/operations/workers")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Worker telemetry storage is unavailable"}
    assert "code=storage_unavailable" in caplog.text


def test_invalid_evidence_is_explicitly_logged_and_sanitized(api, caplog):
    api.dependency_overrides[get_current_user] = lambda: user(UserRole.ADMIN)
    def invalid():
        InstanceStatus.model_validate({"state": "secret-bearing-invalid-data"})
    api.dependency_overrides[status_service] = lambda: SimpleNamespace(read=invalid)
    response = TestClient(api).get("/api/v1/operations/workers")
    assert response.status_code == 503
    assert "code=invalid_evidence" in caplog.text
    assert "secret-bearing-invalid-data" not in response.text + caplog.text


def test_main_mounts_read_only_operations_route():
    from app.main import app
    routes = [r for r in app.routes if getattr(r, "path", "").startswith("/api/v1/operations")]
    assert len(routes) == 1 and routes[0].methods == {"GET"}
