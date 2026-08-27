from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user as auth_get_current_user
from app.auth.schemas import AuthUser
from app.main import app


def test_dashboard_route_returns_simple_contract(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.routes import dashboard as dashboard_router

    app.dependency_overrides[dashboard_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )

    class _FakeDashboardService:
        def __init__(self):
            self.calls = []

        def get_dashboard(self, db, team_id=None):
            self.calls.append((db, team_id))
            return {
                "system_health": "healthy",
                "overall_accuracy": 72.5,
                "total_predictions": 2,
                "recent_predictions": ["p1", "p2"],
                "top_teams": [],
                "model_versions": [{"model": "NPI-v1", "accuracy": 72.5}],
            }

    service = _FakeDashboardService()
    monkeypatch.setattr(dashboard_router, "DashboardService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    assert service.calls == [(fake_db, None)]
    assert response.json() == {
        "system_health": "healthy",
        "overall_accuracy": 72.5,
        "total_predictions": 2,
        "recent_predictions": ["p1", "p2"],
        "top_teams": [],
        "model_versions": [{"model": "NPI-v1", "accuracy": 72.5}],
        "model_lab": None,
    }

    app.dependency_overrides.clear()


def test_dashboard_route_accepts_team_id_query(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.routes import dashboard as dashboard_router

    app.dependency_overrides[dashboard_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )

    class _FakeDashboardService:
        def __init__(self):
            self.calls = []

        def get_dashboard(self, db, team_id=None):
            self.calls.append((db, team_id))
            return {
                "system_health": "healthy",
                "overall_accuracy": 80.1,
                "total_predictions": 3,
                "recent_predictions": ["p1", "p2", "p3"],
                "top_teams": [
                    {
                        "team_id": 11,
                        "team_name": "Atlanta Dream",
                        "momentum": 80.0,
                        "strength_rating": 84.3,
                    }
                ],
                "model_versions": [{"model": "NPI-v2", "accuracy": 80.1}],
            }

    service = _FakeDashboardService()
    monkeypatch.setattr(dashboard_router, "DashboardService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/dashboard", params={"team_id": 11})

    assert response.status_code == 200
    assert service.calls == [(fake_db, 11)]
    assert response.json()["top_teams"] == [
        {
            "team_id": 11,
            "team_name": "Atlanta Dream",
            "momentum": 80.0,
            "strength_rating": 84.3,
        }
    ]

    app.dependency_overrides.clear()
