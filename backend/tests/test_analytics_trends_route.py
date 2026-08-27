from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user as auth_get_current_user
from app.auth.schemas import AuthUser
from app.main import app


def _override_db(fake_db):
    def _get_db():
        yield fake_db

    return _get_db


def test_daily_weekly_monthly_trend_routes(monkeypatch):
    fake_db = object()

    from app.api.v1 import analytics as analytics_router

    app.dependency_overrides[analytics_router.get_db] = _override_db(fake_db)
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )

    class _FakeTrendService:
        def __init__(self):
            self.calls = []

        def daily_trends(self, db):
            self.calls.append(("daily", db))
            return [
                {
                    "period": "2026-01-01",
                    "accuracy": 50.0,
                    "confidence": 70.0,
                    "predictions": 2,
                    "correct": 1,
                }
            ]

        def weekly_trends(self, db):
            self.calls.append(("weekly", db))
            return [
                {
                    "period": "2026-W01",
                    "accuracy": 66.67,
                    "confidence": 72.0,
                    "predictions": 3,
                    "correct": 2,
                }
            ]

        def monthly_trends(self, db):
            self.calls.append(("monthly", db))
            return [
                {
                    "period": "2026-01",
                    "accuracy": 66.67,
                    "confidence": 72.0,
                    "predictions": 3,
                    "correct": 2,
                }
            ]

    fake_service = _FakeTrendService()
    monkeypatch.setattr(analytics_router, "HistoricalTrendService", lambda: fake_service)

    client = TestClient(app)

    assert client.get("/api/v1/analytics/trends/daily").json() == [
        {
            "period": "2026-01-01",
            "accuracy": 50.0,
            "confidence": 70.0,
            "predictions": 2,
            "correct": 1,
        }
    ]
    assert client.get("/api/v1/analytics/trends/weekly").json() == [
        {
            "period": "2026-W01",
            "accuracy": 66.67,
            "confidence": 72.0,
            "predictions": 3,
            "correct": 2,
        }
    ]
    assert client.get("/api/v1/analytics/trends/monthly").json() == [
        {
            "period": "2026-01",
            "accuracy": 66.67,
            "confidence": 72.0,
            "predictions": 3,
            "correct": 2,
        }
    ]

    assert fake_service.calls == [
        ("daily", fake_db),
        ("weekly", fake_db),
        ("monthly", fake_db),
    ]

    app.dependency_overrides.clear()


def test_scoped_trend_routes(monkeypatch):
    fake_db = object()

    from app.api.v1 import analytics as analytics_router

    app.dependency_overrides[analytics_router.get_db] = _override_db(fake_db)
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )

    class _FakeTrendService:
        def __init__(self):
            self.calls = []

        def team_trends(self, db, team_id):
            self.calls.append(("team", db, team_id))
            return {
                "team": "Atlanta Dream",
                "last30": {"accuracy": 74.2, "momentum": 86.4},
            }

        def sport_trends(self, db, sport):
            self.calls.append(("sport", db, sport))
            return [
                {"sport": "NBA", "accuracy": 72.8},
                {"sport": "WNBA", "accuracy": 75.1},
            ]

        def model_trends(self, db, version):
            self.calls.append(("model", db, version))
            return [
                {"version": "NPI-v1", "accuracy": 68.2},
                {"version": "NPI-v2", "accuracy": 72.9},
            ]

    fake_service = _FakeTrendService()
    monkeypatch.setattr(analytics_router, "HistoricalTrendService", lambda: fake_service)

    client = TestClient(app)

    assert client.get("/api/v1/analytics/trends/team/11").json() == {
        "team": "Atlanta Dream",
        "last30": {"accuracy": 74.2, "momentum": 86.4},
    }
    assert client.get("/api/v1/analytics/trends/sport").json() == [
        {"sport": "NBA", "accuracy": 72.8},
        {"sport": "WNBA", "accuracy": 75.1},
    ]
    assert client.get("/api/v1/analytics/trends/model").json() == [
        {"version": "NPI-v1", "accuracy": 68.2},
        {"version": "NPI-v2", "accuracy": 72.9},
    ]

    assert fake_service.calls == [
        ("team", fake_db, 11),
        ("sport", fake_db, None),
        ("model", fake_db, None),
    ]

    app.dependency_overrides.clear()
