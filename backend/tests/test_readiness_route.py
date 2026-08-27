from app.main import app


def test_readiness_route_exists():
    routes = {route.path for route in app.routes}

    assert "/api/v1/readiness" in routes