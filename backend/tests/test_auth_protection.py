from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.jwt import JWTError
from app.auth.jwt import JWTService
from app.auth.service import AuthenticationService
from app.main import app


def test_protected_dashboard_requires_authentication():
    client = TestClient(app)

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token"


def test_inactive_user_cannot_authenticate():
    class _FakeUserRepository:
        def get_by_email(self, _db, _email):
            return SimpleNamespace(
                id=2,
                username="inactive",
                email="inactive@example.com",
                hashed_password="$argon2id$v=19$m=65536,t=3,p=4$dummy",
                role="user",
                is_active=False,
            )

    service = AuthenticationService(user_repository=_FakeUserRepository())

    token = service.login(
        db=object(),
        email="inactive@example.com",
        password="any-password",
    )

    assert token is None


def test_current_user_rejects_expired_token():
    service = AuthenticationService()

    expired_access_token, _, _ = JWTService().create_access_token(
        {
            "sub": "admin@nik.ai",
            "type": "access",
            "role": "admin",
        },
        expires_delta=timedelta(seconds=-1),
    )

    try:
        service.current_user(db=object(), token=expired_access_token)
        assert False, "Expected JWTError for expired token"
    except JWTError as exc:
        assert str(exc) == "Token expired"
