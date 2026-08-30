from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import auth as auth_routes
from app.api.v1 import premium, product, subscriptions
from app.auth.dependencies import get_auth_service
from app.auth.jwt import JWTService
from app.auth.service import AuthenticationService
from app.database.session import get_db
from app.main import app


class _EmptyUserRepository:
    def get_by_email(self, _db, _email):
        return None


def _auth_client() -> TestClient:
    auth_app = FastAPI()
    auth_app.include_router(auth_routes.router, prefix="/api/v1")
    auth_app.dependency_overrides[get_db] = lambda: object()
    auth_app.dependency_overrides[get_auth_service] = lambda: AuthenticationService(
        user_repository=_EmptyUserRepository()
    )
    return TestClient(auth_app)


def test_login_and_me_flow():
    client = _auth_client()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )

    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": 0,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
        "email_verified": False,
    }


def test_login_token_authenticates_users_me_route(monkeypatch):
    monkeypatch.setattr(
        product.service,
        "get_saved_picks",
        lambda **_: {"count": 0, "picks": []},
    )
    monkeypatch.setattr(
        subscriptions,
        "get_user_subscription",
        lambda *_: {
            "id": None,
            "plan": "free",
            "active": False,
            "created_at": None,
        },
    )
    monkeypatch.setattr(premium, "require_premium", lambda *_: True)
    client = TestClient(app)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )

    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["role"] == "admin"

    saved_picks_response = client.get(
        "/api/v1/product/me/saved-picks",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert saved_picks_response.status_code == 200

    subscription_response = client.get(
        "/api/v1/subscriptions/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    premium_response = client.get(
        "/api/v1/premium/advanced-analysis",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert subscription_response.status_code == 200
    assert premium_response.status_code == 200


def test_login_rejects_invalid_credentials():
    client = _auth_client()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_rejects_unknown_user():
    client = _auth_client()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "secret"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_me_requires_bearer_token():
    client = _auth_client()

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_me_rejects_expired_token():
    client = _auth_client()

    expired, _, _ = JWTService().create_access_token(
        {
            "sub": "admin@example.com",
            "type": "access",
            "role": "admin",
        },
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_refresh_returns_fresh_access_token():
    client = _auth_client()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    token_data = login_response.json()

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["token_type"] == "bearer"
    assert isinstance(refreshed["access_token"], str)
    assert len(refreshed["access_token"]) > 20


def test_protected_predictions_endpoint_rejects_anonymous_request():
    client = TestClient(app)

    response = client.get("/api/v1/predictions/1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"
