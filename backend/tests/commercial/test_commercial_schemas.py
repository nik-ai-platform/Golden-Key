from fastapi.testclient import TestClient

from app.auth.dependencies import require_admin
from app.main import app


client = TestClient(app)


def test_commercial_payloads_use_schema_models():
    app.dependency_overrides[require_admin] = lambda: None
    response = client.post(
        "/api/v1/commercial/subscriptions",
        json={"plan": "PRO", "user_id": 5},
    )
    assert response.status_code == 200
    assert response.json()["plan"] == "PRO"

    response = client.post(
        "/api/v1/commercial/api-keys",
        json={"owner": 11, "quota": 250},
    )
    assert response.status_code == 200
    assert response.json()["quota"] == 250

    response = client.post(
        "/api/v1/commercial/organizations",
        json={"name": "Acme", "owner_id": 77},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Acme"

    response = client.get("/api/v1/commercial/permissions/premium_features", params={"role": "PREMIUM"})
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    app.dependency_overrides.clear()
