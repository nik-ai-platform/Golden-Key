from fastapi.testclient import TestClient

from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.main import app



def test_prediction_outcomes_route_lists_outcomes(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import prediction_outcomes as outcomes_router

    app.dependency_overrides[outcomes_router.get_db] = _override_get_db
    app.dependency_overrides[require_viewer] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="viewer",
        is_active=True,
    )

    class _FakeOutcomeService:
        def __init__(self):
            self.calls = []

        def list_outcomes(self, db, limit=100):
            self.calls.append((db, limit))
            return [
                {
                    "id": 1,
                    "prediction_id": 10,
                    "game_id": 20,
                    "predicted_winner": "Home Team",
                    "actual_winner": "Home Team",
                    "predicted_confidence": 92.0,
                    "prediction_correct": True,
                    "point_spread_error": 0.0,
                    "created_at": "2026-07-25T00:00:00",
                }
            ]

    service = _FakeOutcomeService()
    monkeypatch.setattr(outcomes_router, "PredictionOutcomeService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/predictions/outcomes")

    assert response.status_code == 200
    assert service.calls == [(fake_db, 100)]
    assert response.json()[0]["prediction_id"] == 10

    app.dependency_overrides.clear()



def test_prediction_outcomes_route_returns_single_outcome(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import prediction_outcomes as outcomes_router

    app.dependency_overrides[outcomes_router.get_db] = _override_get_db
    app.dependency_overrides[require_viewer] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="viewer",
        is_active=True,
    )

    class _FakeOutcomeService:
        def __init__(self):
            self.calls = []

        def get_outcome_by_prediction_id(self, db, prediction_id):
            self.calls.append((db, prediction_id))
            return {
                "id": 7,
                "prediction_id": prediction_id,
                "game_id": 99,
                "predicted_winner": "Away Team",
                "actual_winner": "Home Team",
                "predicted_confidence": 65.0,
                "prediction_correct": False,
                "point_spread_error": 4.5,
                "created_at": "2026-07-25T00:00:00",
            }

    service = _FakeOutcomeService()
    monkeypatch.setattr(outcomes_router, "PredictionOutcomeService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/predictions/outcomes/7")

    assert response.status_code == 200
    assert service.calls == [(fake_db, 7)]
    assert response.json()["prediction_id"] == 7

    app.dependency_overrides.clear()
