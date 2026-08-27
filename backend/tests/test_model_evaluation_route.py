from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.auth.dependencies import require_analyst
from app.auth.dependencies import require_admin
from app.auth.dependencies import get_current_user as auth_get_current_user
from app.auth.schemas import AuthUser
from app.main import app
from app.models.model_performance import ModelPerformance


def test_models_list_route_returns_registry_rows():
    rows = [
        type(
            "Row",
            (),
            {
                "model_version": "NPI-v3",
                "accuracy": 71.8,
                "average_confidence": 81.2,
                "total_predictions": 2184,
            },
        )(),
        type(
            "Row",
            (),
            {
                "model_version": "NPI-v4",
                "accuracy": 73.4,
                "average_confidence": 79.8,
                "total_predictions": 2184,
            },
        )(),
    ]

    class _Query:
        def __init__(self, model):
            self.model = model

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return rows

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return rows[0]

    class _FakeDB:
        def query(self, _model):
            return _Query(_model)

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import models as models_router

    app.dependency_overrides[models_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = lambda: AuthUser(
        id=1,
        username="analyst",
        email="analyst@example.com",
        role="analyst",
        is_active=True,
    )

    client = TestClient(app)
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["model_version"] == "NPI-v3"
    assert payload[1]["evaluation_metrics"]["accuracy"] == 73.4

    app.dependency_overrides.clear()


def test_models_compare_route_uses_identical_payload_dataset():
    class _Query:
        def __init__(self):
            pass

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return type(
                "Row",
                (),
                {
                    "model_version": "NPI-v3",
                    "accuracy": 71.8,
                    "average_confidence": 81.2,
                    "total_predictions": 2184,
                },
            )()

    class _FakeDB:
        def query(self, _model):
            assert _model is ModelPerformance
            return _Query()

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import models as models_router

    app.dependency_overrides[models_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = lambda: AuthUser(
        id=1,
        username="analyst",
        email="analyst@example.com",
        role="analyst",
        is_active=True,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/models/compare",
        json={
            "current_version": "NPI-v3",
            "candidate_version": "NPI-v4",
            "games": [
                {
                    "actual_winner": "HOME",
                    "predictions": {
                        "NPI-v3": {"winner": "HOME", "confidence": 82.0},
                        "NPI-v4": {"winner": "HOME", "confidence": 79.0},
                    },
                },
                {
                    "actual_winner": "AWAY",
                    "predictions": {
                        "NPI-v3": {"winner": "HOME", "confidence": 77.0},
                        "NPI-v4": {"winner": "AWAY", "confidence": 75.0},
                    },
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_model"]["predictions"] == 2
    assert payload["candidate_model"]["predictions"] == 2

    app.dependency_overrides.clear()


def test_admin_can_promote_active_model_version(monkeypatch):
    class _FakeRegistry:
        def __init__(self):
            self.active = "nba-v1"

        def set_active_version(self, sport, version):
            if sport != "basketball_nba":
                raise Exception("unexpected sport")
            self.active = version.lower()

        def get_active_version(self, _sport):
            return self.active

        def list_versions(self, _sport):
            return ["nba-v1", "nba-v2"]

    class _FakeVersionService:
        def __init__(self):
            self.sport_versions = {}

        def set_version_for_sport(self, sport, version):
            self.sport_versions[sport] = version

        def rollback_version_for_sport(self, sport):
            return self.sport_versions.get(sport, "NBA-v1")

        def get_version_for_sport(self, sport, default=None):
            return self.sport_versions.get(sport, default)

    fake_runtime = type(
        "RuntimeService",
        (),
        {
            "model_registry": _FakeRegistry(),
            "version_service": _FakeVersionService(),
        },
    )()

    from app.api.v1 import models as models_router

    monkeypatch.setattr(models_router, "_prediction_runtime_service", lambda: fake_runtime)

    app.dependency_overrides[require_analyst] = lambda: AuthUser(
        id=1,
        username="admin",
        email="admin@example.com",
        role="admin",
        is_active=True,
    )
    app.dependency_overrides[require_admin] = lambda: AuthUser(
        id=1,
        username="admin",
        email="admin@example.com",
        role="admin",
        is_active=True,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/models/active-version",
        json={
            "sport": "basketball_nba",
            "action": "promote",
            "version": "NBA-v2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_version"] == "nba-v2"

    app.dependency_overrides.clear()


def test_analyst_cannot_promote_active_model_version(monkeypatch):
    class _FakeRegistry:
        def set_active_version(self, _sport, _version):
            raise HTTPException(status_code=500, detail="should not be called")

    fake_runtime = type(
        "RuntimeService",
        (),
        {
            "model_registry": _FakeRegistry(),
            "version_service": object(),
        },
    )()

    from app.api.v1 import models as models_router

    monkeypatch.setattr(models_router, "_prediction_runtime_service", lambda: fake_runtime)
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=2,
        username="analyst",
        email="analyst@example.com",
        role="analyst",
        is_active=True,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/models/active-version",
        json={
            "sport": "basketball_nba",
            "action": "promote",
            "version": "NBA-v2",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}

    app.dependency_overrides.clear()