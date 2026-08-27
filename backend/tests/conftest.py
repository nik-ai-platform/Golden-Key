import os


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
