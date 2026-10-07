import os
import pytest


# Ensure unit tests can import app modules without requiring manual shell env setup.
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPORTSBOOK_API_KEYS", '{"odds_api":"test"}')
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault(
    "SMTP_SETTINGS",
    '{"host":"smtp.test","port":25,"username":"u","password":"p","from_email":"noreply@test","use_tls":false}',
)
os.environ.setdefault("AUTH_DEMO_EMAIL", "admin@example.com")
os.environ.setdefault("AUTH_DEMO_PASSWORD", "admin123")


@pytest.fixture
def admin_api_contract():
    from app.auth.dependencies import get_current_user
    from app.auth.schemas import AuthUser
    from app.main import app

    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1, username="contract_admin", email="contract.admin@example.com",
        role="admin", is_active=True,
    )
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)
