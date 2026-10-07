import os
from pathlib import Path
import subprocess
import sys
import unittest


IMPORT_PROBE = """
import importlib
import importlib.util
from typing import get_args, get_type_hints

modules = (
    "app.database.telemetry_session",
    "app.database.worker_ownership",
    "app.models.worker_instance",
    "app.models.worker_cycle",
    "app.models.worker_cycle_source",
    "app.services.worker_telemetry_service",
    "app.workers.worker_instrumentation",
    "app.workers.final_score_worker",
    "app.workers.upcoming_game_worker",
    "scripts.prune_worker_telemetry",
)
for name in modules:
    importlib.import_module(name)
    print("IMPORTED=" + name)
spec = importlib.util.spec_from_file_location(
    "telemetry_migration",
    "migrations/versions/e7b4c2d9a610_add_worker_observability.py",
)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
assert migration.revision == "e7b4c2d9a610"
from app.database.telemetry_session import TelemetryDatabase
annotation = get_type_hints(TelemetryDatabase.transaction.__wrapped__)["return"]
assert len(get_args(annotation)) == 3
print("PRODUCTION_MODULE_IMPORTS=PASS")
"""


STARTUP_PROBE = """
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import sys

from app.core.config import settings
from app.database.telemetry_session import telemetry_database
from app.workers.worker_instrumentation import ACTIVE

worker = importlib.import_module("app.workers." + sys.argv[1])
assert settings.OPERATIONS_TELEMETRY_ENABLED is False
assert telemetry_database._engine is None
assert telemetry_database._factory is None
db = MagicMock()
original_exit = SystemExit(23)
sleeps = []
def sleep(seconds):
    sleeps.append(seconds)
    raise original_exit
def forbidden(*args, **kwargs):
    raise AssertionError("Disabled worker touched telemetry storage")
common = {
    "_configured_sports": lambda: ("NBA",),
    "_poll_seconds": lambda: 900,
    "SessionLocal": MagicMock(return_value=db),
}
if sys.argv[1] == "upcoming_game_worker":
    importer = MagicMock()
    importer.import_games.return_value = []
    importer.source_imports = []
    business = {
        "GameOddsImporter": MagicMock(return_value=importer),
        "PredictionEngine": MagicMock(),
    }
else:
    summary = SimpleNamespace(sport="NBA", **{
        name: 0 for name in (
            "fetched", "matched", "finalized", "already_final", "unmatched",
            "skipped_not_final", "settled", "errors",
        )
    })
    service = MagicMock()
    service.sync_sport.return_value = summary
    business = {
        "OddsProviderClient": MagicMock(),
        "FinalScoreSettlementService": MagicMock(return_value=service),
    }
with (
    patch.multiple(worker, **common, **business),
    patch.object(worker.time, "sleep", sleep),
    patch("app.database.telemetry_session.create_engine", forbidden),
    patch("app.database.worker_ownership.create_engine", forbidden),
    patch("app.database.worker_ownership.WorkerOwnership.acquire", forbidden),
    patch.object(telemetry_database, "transaction", forbidden),
):
    try:
        worker.run_forever()
    except SystemExit as error:
        assert error is original_exit
    else:
        raise AssertionError("Worker lost its original exit")
common["SessionLocal"].assert_called_once_with()
db.close.assert_called_once_with()
db.rollback.assert_not_called()
if sys.argv[1] == "upcoming_game_worker":
    importer.import_games.assert_called_once_with("NBA")
    business["PredictionEngine"].assert_called_once_with()
    assert sleeps == [900]
else:
    service.sync_sport.assert_called_once_with(db, "NBA", days_from=3)
    assert len(sleeps) == 1 and 1 <= sleeps[0] <= 900
assert ACTIVE.get() is None
assert telemetry_database._engine is None
assert telemetry_database._factory is None
print("DISABLED_WORKER_STARTUP=PASS worker=" + sys.argv[1])
"""


class WorkerProductionRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("REQUIRE_PRODUCTION_PYTHON312") == "1":
            if sys.version_info[:2] != (3, 12):
                raise AssertionError("Production image must run Python 3.12")

    def run_probe(self, code, *args):
        environment = os.environ.copy()
        environment.update({
            "ENVIRONMENT": "testing",
            "DATABASE_URL": "sqlite:///:memory:",
            "OPERATIONS_TELEMETRY_ENABLED": "false",
            "JWT_SECRET": "test-secret",
            "SECRET_KEY": "test-secret",
            "ODDS_API_KEY": "test-key",
            "OPENAI_API_KEY": "test-key",
            "SPORTSBOOK_API_KEYS": '{"odds_api":"test"}',
            "REDIS_URL": "redis://localhost:6379/0",
            "SMTP_SETTINGS": "{}",
            "AUTH_DEMO_EMAIL": "admin@example.com",
            "AUTH_DEMO_PASSWORD": "admin123",
        })
        result = subprocess.run(
            [sys.executable, "-B", "-c", code, *args],
            cwd=Path(__file__).resolve().parents[1],
            env=environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_all_telemetry_and_worker_modules_import_in_fresh_interpreter(self):
        self.assertIn("PRODUCTION_MODULE_IMPORTS=PASS", self.run_probe(IMPORT_PROBE))

    def test_upcoming_disabled_worker_starts_and_completes_one_polling_pass(self):
        self.assertIn("DISABLED_WORKER_STARTUP=PASS", self.run_probe(STARTUP_PROBE, "upcoming_game_worker"))

    def test_final_score_disabled_worker_starts_and_completes_one_polling_pass(self):
        self.assertIn("DISABLED_WORKER_STARTUP=PASS", self.run_probe(STARTUP_PROBE, "final_score_worker"))


if __name__ == "__main__":
    unittest.main()
