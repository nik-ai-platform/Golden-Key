from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_security_headers():
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_permissions_policy():
    response = client.get("/health")
    policy = response.headers["permissions-policy"]

    assert "camera=()" in policy
    assert "microphone=()" in policy