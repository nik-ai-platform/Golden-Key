from types import SimpleNamespace
from datetime import datetime

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


class _PredictionQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return [
            SimpleNamespace(
                id=11,
                game_id=1,
                market="spread",
                selection="HOME",
                line_value=-4.5,
                american_odds=-110,
                model_version="NPI-4.0",
                npi_score=110.0,
                confidence_score=75.0,
                simulation_probability=62.0,
                projected_edge=8.0,
                risk_level="medium",
                reasoning="Spread model.",
            )
        ]


class _PredictionDB:
    def query(self, _model):
        return _PredictionQuery()


def _prediction_game():
    return SimpleNamespace(
        id=1,
        sport="NBA",
        game_date=datetime(2026, 8, 30, 12, 0),
        home_team=SimpleNamespace(name="Home Team"),
        away_team=SimpleNamespace(name="Away Team"),
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
    fake_db = _PredictionDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import predictions as predictions_router

    app.dependency_overrides[predictions_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: _user("analyst")

    monkeypatch.setattr(
        predictions_router.game_repository,
        "get_game_with_teams",
        lambda *_: _prediction_game(),
    )

    client = TestClient(app)
    response = client.get("/api/v1/predictions/1")

    assert response.status_code == 200
    assert response.json()[0]["game_id"] == 1

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
    fake_db = _PredictionDB()

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
        predictions_router.game_repository,
        "get_game_with_teams",
        lambda *_: _prediction_game(),
    )

    client = TestClient(app)

    dashboard = client.get("/api/v1/dashboard")
    imports = client.post("/api/v1/imports/nba")
    predictions = client.get("/api/v1/predictions/1")

    assert dashboard.status_code == 200
    assert imports.status_code == 200
    assert predictions.status_code == 200

    app.dependency_overrides.clear()
