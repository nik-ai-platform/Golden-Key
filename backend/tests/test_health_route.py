from app.api.routes.health import health_check, ready_check


class _ReadyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement):
        return None


class _ReadyEngine:
    def connect(self):
        return _ReadyConnection()


def test_health():

    result = health_check()

    assert result["status"] == "healthy"


def test_ready():

    from app.api.routes import health as health_module

    original_engine = health_module.engine
    health_module.engine = _ReadyEngine()

    try:
        result = ready_check()
    finally:
        health_module.engine = original_engine

    assert result["status"] == "healthy"
    assert result["database"] == "connected"
