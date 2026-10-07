import threading
from unittest.mock import Mock, call

import pytest

from app.database.telemetry_session import TelemetryConfig, TelemetryDatabase, TelemetryError
from app.services.worker_telemetry_service import PruneSummary
from app.workers import telemetry_retention_worker as worker


@pytest.mark.parametrize("enabled,locked,code", [(True, True, 0), (True, False, 2), (False, False, 0)])
def test_once_and_dry_run_default(monkeypatch, enabled, locked, code):
    database = Mock()
    service = Mock()
    service.prune_history.return_value = PruneSummary(enabled, True, locked)
    monkeypatch.setattr(worker, "WorkerTelemetryService", lambda _db: service)
    assert worker.run_retention(database=database, once=True) == code
    assert service.prune_history.call_args.kwargs["dry_run"] is True
    assert service.prune_history.call_args.kwargs["batch_size"] == 500
    database.dispose.assert_called_once()


def test_disabled_scheduler_does_not_open_storage(monkeypatch):
    db = TelemetryDatabase("postgresql://invalid", TelemetryConfig())
    monkeypatch.setattr(db, "transaction", lambda: pytest.fail("Disabled retention accessed storage"))
    assert worker.run_retention(database=db, once=True) == 0


@pytest.mark.parametrize("kwargs", [{"interval_seconds": 59}, {"interval_seconds": 86401}, {"retention_days": 0}, {"batch_size": 501}])
def test_bounds_fail_before_service_access(monkeypatch, kwargs):
    monkeypatch.setattr(worker, "WorkerTelemetryService", lambda _db: pytest.fail("Invalid settings opened storage"))
    with pytest.raises(ValueError):
        worker.run_retention(**kwargs)


def test_storage_failure_logs_and_disposes(monkeypatch, caplog):
    db = Mock()
    service = Mock()
    service.prune_history.side_effect = TelemetryError("storage_unavailable")
    monkeypatch.setattr(worker, "WorkerTelemetryService", lambda _db: service)
    assert worker.run_retention(database=db, once=True) == 1
    assert "code=storage_unavailable" in caplog.text
    db.dispose.assert_called_once()


def test_schedule_is_serial_and_waits_without_retry_burst(monkeypatch):
    db = Mock()
    stop = Mock(spec=threading.Event)
    stop.is_set.side_effect = [False, False, True]
    service = Mock()
    service.prune_history.side_effect = [
        TelemetryError("storage_unavailable"), PruneSummary(True, False, True),
    ]
    monkeypatch.setattr(worker, "WorkerTelemetryService", lambda _db: service)
    assert worker.run_retention(database=db, dry_run=False, stop=stop, interval_seconds=60) == 0
    assert service.prune_history.call_count == 2
    assert stop.wait.call_args_list == [call(60), call(60)]
    assert service.prune_history.call_args.kwargs["dry_run"] is False
    db.dispose.assert_called_once()


def test_cli_apply_and_once_are_explicit(monkeypatch):
    run = Mock(return_value=0)
    monkeypatch.setattr(worker, "run_retention", run)
    assert worker.main(["--once"]) == 0
    assert run.call_args.kwargs["dry_run"] is True
    assert worker.main(["--apply", "--once", "--batch-size", "1"]) == 0
    assert run.call_args.kwargs["dry_run"] is False and run.call_args.kwargs["batch_size"] == 1
    with pytest.raises(SystemExit):
        worker.main(["--apply", "--dry-run"])


def test_interruption_preserves_exception_and_disposes(monkeypatch):
    db = Mock()
    service = Mock()
    service.prune_history.side_effect = KeyboardInterrupt()
    monkeypatch.setattr(worker, "WorkerTelemetryService", lambda _db: service)
    with pytest.raises(KeyboardInterrupt):
        worker.run_retention(database=db)
    db.dispose.assert_called_once()
