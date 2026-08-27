from app.core.config import settings


def test_environment_settings_support_multiple_backends():
    assert settings.ENVIRONMENT in {"development", "testing", "staging", "production"}
    assert settings.DATABASE_URL
    assert settings.REDIS_URL
    assert settings.STORAGE_BACKEND


def test_secret_management_settings_present():
    assert settings.SECRET_KEY
    assert settings.JWT_SECRET_KEY
