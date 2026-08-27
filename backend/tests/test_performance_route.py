from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user as auth_get_current_user
from app.auth.schemas import AuthUser
from app.database.session import get_db
from app.main import app


class _Result:
    def __init__(self, outcome: str):
        self.outcome = outcome


class _Query:
    def all(self):
        return [_Result("WIN"), _Result("LOSS"), _Result("WIN")]


class _FakeSession:
    def query(self, _model):
        return _Query()


def test_performance_route_returns_metrics_snapshot():
    app.dependency_overrides[auth_get_current_user] = lambda: AuthUser(
        id=1,
        username="tester",
        email="tester@example.com",
        role="admin",
        is_active=True,
    )
    app.dependency_overrides[get_db] = lambda: _FakeSession()

    client = TestClient(app)
    response = client.get("/api/v1/analytics/performance")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "total_predictions": 3,
        "wins": 2,
        "losses": 1,
        "accuracy": 66.67,
    }

    app.dependency_overrides.clear()