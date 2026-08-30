from fastapi.testclient import TestClient

from app.auth.dependencies import require_admin
from app.main import app


client = TestClient(app)


def test_commercial_routes_are_exposed():
    app.dependency_overrides[require_admin] = lambda: None
    response = client.post("/api/v1/commercial/subscriptions", params={"plan": "PRO", "user_id": 7})
    assert response.status_code == 200

    response = client.get("/api/v1/commercial/subscriptions")
    assert response.status_code == 200

    response = client.post("/api/v1/commercial/billing/webhook")
    assert response.status_code == 200

    response = client.post("/api/v1/commercial/api-keys", params={"owner": 42, "quota": 200})
    assert response.status_code == 200

    response = client.get("/api/v1/commercial/admin/users")
    assert response.status_code == 200

    response = client.get("/api/v1/commercial/admin/metrics")
    assert response.status_code == 200

    response = client.get("/api/v1/commercial/admin/audit")
    assert response.status_code == 200
    app.dependency_overrides.clear()
