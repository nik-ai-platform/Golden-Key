from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.dependencies import require_analyst
from app.auth.schemas import AuthUser
from app.main import app
from app.models.nik_score import NikScore
from app.models.prediction_snapshot import PredictionSnapshot


def test_prediction_explanation_route_returns_expected_contract(monkeypatch):
    prediction = SimpleNamespace(
        id=1421,
        game_id=100,
        home_score=111.2,
        away_score=104.7,
        recommendation="Boston Celtics",
        confidence=87.4,
    )
    snapshot = SimpleNamespace(
        id=900,
        game_id=100,
        home_features={"momentum": 92, "market_odds": 70},
        away_features={"momentum": 48},
    )

    class _Query:
        def __init__(self, result):
            self.result = result

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def first(self):
            return self.result

    class _FakeDB:
        def query(self, model):
            if model is NikScore:
                return _Query(prediction)
            if model is PredictionSnapshot:
                return _Query(snapshot)
            return _Query(None)

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import predictions as predictions_router

    app.dependency_overrides[predictions_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = lambda: AuthUser(
        id=1,
        username="analyst",
        email="analyst@example.com",
        role="analyst",
        is_active=True,
    )

    def _fake_explain(prediction_obj, features=None):
        assert prediction_obj.id == 1421
        assert features == {"momentum": 92, "market_odds": 70}
        return {
            "prediction_id": 1421,
            "winner": "Boston Celtics",
            "confidence": 87.4,
            "top_positive": [
                {
                    "feature": "Momentum",
                    "value": 92.0,
                    "weight": 0.25,
                    "contribution": 10.5,
                }
            ],
            "top_negative": [
                {
                    "feature": "Market Odds",
                    "value": 70.0,
                    "weight": 0.15,
                    "contribution": -3.0,
                }
            ],
        }

    monkeypatch.setattr(predictions_router.importance_service, "explain_prediction", _fake_explain)

    client = TestClient(app)
    response = client.get("/api/v1/predictions/1421/explanation")

    assert response.status_code == 200
    assert response.json()["prediction_id"] == 1421
    assert response.json()["top_positive"][0]["feature"] == "Momentum"
    assert response.json()["top_negative"][0]["feature"] == "Market Odds"

    app.dependency_overrides.clear()


def test_prediction_explanation_route_returns_404_when_missing_prediction():
    class _Query:
        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def first(self):
            return None

    class _FakeDB:
        def query(self, _model):
            return _Query()

    fake_db = _FakeDB()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import predictions as predictions_router

    app.dependency_overrides[predictions_router.get_db] = _override_get_db
    app.dependency_overrides[require_analyst] = lambda: AuthUser(
        id=1,
        username="analyst",
        email="analyst@example.com",
        role="analyst",
        is_active=True,
    )

    client = TestClient(app)
    response = client.get("/api/v1/predictions/9999/explanation")

    assert response.status_code == 404
    assert response.json() == {"detail": "Prediction not found"}

    app.dependency_overrides.clear()