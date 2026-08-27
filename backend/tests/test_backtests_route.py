from datetime import date

from fastapi.testclient import TestClient

from app.auth.dependencies import require_analyst
from app.auth.schemas import AuthUser
from app.main import app


def _analyst_user():
    return AuthUser(
        id=1,
        username="analyst",
        email="analyst@example.com",
        role="analyst",
        is_active=True,
    )


def test_run_backtest_route_persists_and_returns_summary(monkeypatch):
    class _FakeDB:
        pass

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import backtests as backtests_router

    app.dependency_overrides[backtests_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = _analyst_user

    class _FakeBacktestEngine:
        def run(self, **_kwargs):
            return {
                "backtest_id": 10,
                "model_version": "NBA-NPI-v4",
                "sport": "nba",
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 31),
                "stats": {
                    "games_tested": 2400,
                    "win_pct": 72.4,
                    "ats_record": "1318-1082",
                    "roi": 4.8,
                },
            }

    monkeypatch.setattr(backtests_router, "engine", _FakeBacktestEngine())

    client = TestClient(app)
    response = client.post(
        "/api/v1/backtests/run",
        json={
            "sport": "nba",
            "model_version": "NBA-NPI-v4",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "market": "moneyline",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 10
    assert payload["model"] == "NBA-NPI-v4"
    assert payload["games"] == 2400
    assert payload["accuracy"] == 72.4
    assert payload["roi"] == 4.8
    assert payload["recommendation"] == "promote"
    assert payload["stats"]["games_tested"] == 2400

    app.dependency_overrides.clear()


def test_list_backtests_route_returns_rows():
    class _FakeDB:
        pass

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import backtests as backtests_router

    class _FakeBacktestEngine:
        def run_summaries(self, _db):
            return [
                {
                    "id": 10,
                    "model": "NBA-NPI-v4",
                    "games": 2400,
                    "accuracy": 72.4,
                    "roi": 4.8,
                    "ats_record": "1318-1082",
                }
            ]

        def version_comparison(self, _db):
            return [{"model": "NBA-NPI-v4", "ats": 72.4, "roi": 4.8, "avg_confidence": 68.1}]

    monkeypatch.setattr(backtests_router, "engine", _FakeBacktestEngine())

    app.dependency_overrides[backtests_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = _analyst_user

    client = TestClient(app)
    response = client.get("/api/v1/backtests")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runs"][0]["model"] == "NBA-NPI-v4"
    assert payload["version_comparison"][0]["roi"] == 4.8

    app.dependency_overrides.clear()


def test_get_backtest_route_returns_row(monkeypatch):
    class _FakeDB:
        pass

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import backtests as backtests_router

    class _FakeBacktestEngine:
        def run_summary(self, _db, backtest_id):
            assert backtest_id == 7
            return {
                "id": 7,
                "model": "NBA-NPI-v4",
                "games": 2400,
                "accuracy": 72.4,
                "roi": 4.8,
                "stats": {"average_confidence": 66.2},
                "results": [{"game_id": 1001, "win_loss": "WIN"}],
            }

    monkeypatch.setattr(backtests_router, "engine", _FakeBacktestEngine())

    app.dependency_overrides[backtests_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = _analyst_user

    client = TestClient(app)
    response = client.get("/api/v1/backtests/7")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 7
    assert payload["model"] == "NBA-NPI-v4"
    assert payload["stats"]["average_confidence"] == 66.2

    app.dependency_overrides.clear()


def test_get_backtest_route_returns_404_when_missing(monkeypatch):
    class _FakeDB:
        pass

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import backtests as backtests_router

    class _FakeBacktestEngine:
        def run_summary(self, _db, _backtest_id):
            return {}

    monkeypatch.setattr(backtests_router, "engine", _FakeBacktestEngine())

    app.dependency_overrides[backtests_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = _analyst_user

    client = TestClient(app)
    response = client.get("/api/v1/backtests/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Backtest not found"}

    app.dependency_overrides.clear()