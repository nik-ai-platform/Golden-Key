from fastapi.testclient import TestClient

from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.main import app


def test_feature_importance_route_returns_expected_contract(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import analytics as analytics_router

    app.dependency_overrides[analytics_router.get_db] = _override_get_db
    app.dependency_overrides[require_viewer] = lambda: AuthUser(
        id=1,
        username="viewer",
        email="viewer@example.com",
        role="viewer",
        is_active=True,
    )

    class _FakeFeatureImportanceService:
        def __init__(self):
            self.calls = []

        def historical_importance(self, db):
            self.calls.append(db)
            return [
                {"feature": "Momentum", "average_contribution": 17.3},
                {"feature": "Team Strength", "average_contribution": 15.8},
                {"feature": "Market Odds", "average_contribution": -10.9},
            ]

    service = _FakeFeatureImportanceService()
    monkeypatch.setattr(analytics_router, "FeatureImportanceService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/analytics/feature-importance")

    assert response.status_code == 200
    assert service.calls == [fake_db]
    assert response.json()[0] == {"feature": "Momentum", "average_contribution": 17.3}

    app.dependency_overrides.clear()