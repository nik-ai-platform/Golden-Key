from app.main import app


def test_required_product_routes_exist():
    routes = {route.path for route in app.routes}
    required = {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/users/me",
        "/api/v1/product/predictions/today",
        "/api/v1/product/games/{game_id}",
        "/api/v1/product/me/saved-picks",
        "/api/v1/product/performance",
        "/api/v1/version",
    }

    missing = required - routes

    assert not missing, f"Missing routes: {missing}"
