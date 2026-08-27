from fastapi.testclient import TestClient

from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.main import app



def test_calibration_route_returns_expected_contract(monkeypatch):
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

    class _FakeCalibrationService:
        def __init__(self):
            self.calls = []

        def calculate_calibration(self, db=None, outcomes=None):
            self.calls.append((db, outcomes))
            return {
                "overall_error": 2.4,
                "mean_calibration_error": 1.2,
                "maximum_error": 4.1,
                "bucket_variance": 0.62,
                "overall_reliability": 97.6,
                "total_predictions": 120,
                "buckets": [
                    {
                        "range": "90-100",
                        "confidence": 94.1,
                        "accuracy": 91.8,
                        "error": 2.3,
                        "predictions": 40,
                        "wins": 37,
                        "losses": 3,
                    }
                ],
            }

    service = _FakeCalibrationService()
    monkeypatch.setattr(analytics_router, "CalibrationService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/analytics/calibration")

    assert response.status_code == 200
    assert service.calls == [(fake_db, None)]
    assert response.json()["overall_error"] == 2.4
    assert response.json()["buckets"][0]["range"] == "90-100"

    app.dependency_overrides.clear()
