from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user as auth_get_current_user
from app.auth.schemas import AuthUser
from app.main import app


def test_confidence_analytics_route_returns_distribution(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import analytics as analytics_router

    app.dependency_overrides[analytics_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )

    class _FakeConfidenceService:
        def __init__(self):
            self.calls = []

        def get_confidence_distribution(self, db):
            self.calls.append(db)
            return {
                "average_confidence": 78.3,
                "highest_confidence": 98.1,
                "lowest_confidence": 51.4,
                "buckets": [
                    {
                        "label": "Elite",
                        "predictions": 184,
                        "accuracy": 91.2,
                    }
                ],
            }

    fake_confidence = _FakeConfidenceService()
    monkeypatch.setattr(analytics_router, "ConfidenceService", lambda: fake_confidence)

    client = TestClient(app)
    response = client.get("/api/v1/analytics/confidence")

    assert response.status_code == 200
    assert fake_confidence.calls == [fake_db]
    assert response.json() == {
        "average_confidence": 78.3,
        "highest_confidence": 98.1,
        "lowest_confidence": 51.4,
        "buckets": [
            {
                "label": "Elite",
                "predictions": 184,
                "accuracy": 91.2,
            }
        ],
    }

    app.dependency_overrides.clear()


def test_model_learning_route_returns_learning_summary(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import analytics as analytics_router

    app.dependency_overrides[analytics_router.get_db] = _override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )

    class _FakeAnalyticsService:
        def __init__(self):
            self.calls = []

        def dashboard_statistics(self, db):
            self.calls.append(db)
            return {
                "model_learning": {
                    "current_model": "NPI-v3",
                    "training_samples": 18421,
                    "candidate_models": 3,
                    "best_candidate": "NPI-v4",
                }
            }

    fake_analytics = _FakeAnalyticsService()
    monkeypatch.setattr(analytics_router, "AnalyticsService", lambda: fake_analytics)

    client = TestClient(app)
    response = client.get("/api/v1/analytics/model-learning")

    assert response.status_code == 200
    assert fake_analytics.calls == [fake_db]
    assert response.json() == {
        "current_model": "NPI-v3",
        "training_samples": 18421,
        "candidate_models": 3,
        "best_candidate": "NPI-v4",
    }

    app.dependency_overrides.clear()
