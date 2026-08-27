from types import SimpleNamespace

from fastapi import Depends
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user as auth_get_current_user
from app.auth.dependencies import require_admin
from app.auth.schemas import AuthUser
from app.main import app


def _user(role: str) -> AuthUser:
    return AuthUser(
        id=1,
        username=f"{role}-user",
        email=f"{role}@example.com",
        role=role,
        is_active=True,
    )


def test_viewer_cannot_import_games(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import imports as imports_router

    app.dependency_overrides[imports_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: _user("viewer")

    monkeypatch.setattr(imports_router, "import_sport_games", lambda *_: [1, 2, 3])

    client = TestClient(app)
    response = client.post("/api/v1/imports/nba")

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}

    app.dependency_overrides.clear()


def test_viewer_can_view_dashboard(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.routes import dashboard as dashboard_router

    app.dependency_overrides[dashboard_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: _user("viewer")

    class _FakeDashboardService:
        def get_dashboard(self, _db, team_id=None):
            return {
                "system_health": "healthy",
                "overall_accuracy": 88.0,
                "total_predictions": 1,
                "recent_predictions": ["p1"],
                "top_teams": [],
                "model_versions": [{"model": "NPI-v1", "accuracy": 88.0}],
            }

    monkeypatch.setattr(dashboard_router, "DashboardService", _FakeDashboardService)

    client = TestClient(app)
    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200

    app.dependency_overrides.clear()


def test_analyst_can_run_predictions(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import predictions as predictions_router

    app.dependency_overrides[predictions_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: _user("analyst")

    monkeypatch.setattr(
        predictions_router.service,
        "generate_prediction",
        lambda *_: SimpleNamespace(
            game_id=1,
            home_score=100,
            away_score=90,
            confidence=0.82,
            recommendation="HOME",
        ),
    )

    client = TestClient(app)
    response = client.get("/api/v1/predictions/1")

    assert response.status_code == 200
    assert response.json()["game_id"] == 1

    app.dependency_overrides.clear()


def test_analyst_cannot_manage_users_admin_endpoint():
    mini_app = FastAPI()

    @mini_app.get("/users")
    def manage_users(_user: AuthUser = Depends(require_admin)):
        return {"ok": True}

    mini_app.dependency_overrides[auth_get_current_user] = lambda: _user("analyst")

    client = TestClient(mini_app)
    response = client.get("/users")

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_admin_can_access_everything(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.routes import dashboard as dashboard_router
    from app.api.v1 import imports as imports_router
    from app.api.v1 import predictions as predictions_router

    app.dependency_overrides[dashboard_router.get_db] = _override_get_db
    app.dependency_overrides[imports_router.get_db] = _override_get_db
    app.dependency_overrides[predictions_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: _user("admin")

    class _FakeDashboardService:
        def get_dashboard(self, _db, team_id=None):
            return {
                "system_health": "healthy",
                "overall_accuracy": 88.0,
                "total_predictions": 1,
                "recent_predictions": ["p1"],
                "top_teams": [],
                "model_versions": [{"model": "NPI-v1", "accuracy": 88.0}],
            }

    monkeypatch.setattr(dashboard_router, "DashboardService", _FakeDashboardService)
    monkeypatch.setattr(imports_router, "import_sport_games", lambda *_: [1])
    monkeypatch.setattr(
        predictions_router.service,
        "generate_prediction",
        lambda *_: SimpleNamespace(
            game_id=1,
            home_score=100,
            away_score=90,
            confidence=0.82,
            recommendation="HOME",
        ),
    )

    client = TestClient(app)

    dashboard = client.get("/api/v1/dashboard")
    imports = client.post("/api/v1/imports/nba")
    predictions = client.get("/api/v1/predictions/1")

    assert dashboard.status_code == 200
    assert imports.status_code == 200
    assert predictions.status_code == 200

    app.dependency_overrides.clear()
