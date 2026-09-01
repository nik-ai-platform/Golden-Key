from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.v1 import product
from app.auth.jwt import JWTService
from app.core.config import settings
from app.database.session import get_db
from app.main import app


def _anonymous_product_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(product.router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = lambda: object()
    return TestClient(test_app)


@pytest.mark.parametrize(
    "path",
    (
        "/api/v1/product/predictions/today",
        "/api/v1/product/daily-card",
        "/api/v1/product/games/101",
        "/api/v1/product/performance",
    ),
)
def test_product_reads_reject_anonymous_requests(path):
    response = _anonymous_product_client().get(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_authenticated_product_reads_preserve_response_contracts(monkeypatch):
    prediction = {
        "prediction_id": 57,
        "game_id": 101,
        "sport": "WNBA",
        "home_team": "Las Vegas Aces",
        "away_team": "Minnesota Lynx",
        "game_date": "2026-08-30T19:00:00Z",
        "market": "moneyline",
        "selection": "AWAY",
        "display_selection": "Minnesota Lynx",
        "line_value": None,
        "american_odds": 125,
        "model_version": "NPI-4.0",
        "npi_score": 168.0,
        "confidence_score": 82.5,
        "simulation_probability": 79.2,
        "projected_edge": 6.4,
        "risk_level": "LOW",
        "reasoning": None,
        "outcome": None,
    }
    today = {
        "sport": "WNBA",
        "count": 1,
        "predictions": [prediction],
    }
    daily_card = {
        "sport": "WNBA",
        "generated_at": "2026-08-30T12:00:00Z",
        "count": 1,
        "best_bet": {
            "role": "BEST_BET",
            "label": "Best Bet",
            "ranking_score": 82.5,
            "ranking_reasons": ["82.5% confidence"],
            "prediction": prediction,
        },
        "featured_picks": [],
        "next_best": [],
    }
    game = {
        "game_id": 101,
        "sport": "WNBA",
        "home_team": "Las Vegas Aces",
        "away_team": "Minnesota Lynx",
        "game_date": "2026-08-30T19:00:00Z",
        "home_score": None,
        "away_score": None,
        "predictions": [prediction],
    }
    performance = {
        "total_predictions": 3,
        "wins": 1,
        "losses": 1,
        "pushes": 1,
        "accuracy": 50.0,
        "profit_loss": 0.0,
        "market_performance": [],
        "sport_performance": [],
        "recent_results": [],
    }
    monkeypatch.setattr(product.service, "get_today_predictions", lambda **_: today)
    monkeypatch.setattr(product.service, "get_daily_card", lambda **_: daily_card)
    monkeypatch.setattr(product.service, "get_game_detail", lambda **_: game)
    monkeypatch.setattr(product.service, "get_performance", lambda **_: performance)
    access_token, _, _ = JWTService().create_access_token(
        {
            "sub": settings.AUTH_DEMO_EMAIL,
            "role": "admin",
            "uid": 0,
        }
    )
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {access_token}"}

    predictions_response = client.get(
        "/api/v1/product/predictions/today?sport=WNBA",
        headers=headers,
    )
    daily_card_response = client.get(
        "/api/v1/product/daily-card?sport=WNBA",
        headers=headers,
    )
    game_response = client.get("/api/v1/product/games/101", headers=headers)
    performance_response = client.get(
        "/api/v1/product/performance",
        headers=headers,
    )

    assert predictions_response.status_code == 200
    assert predictions_response.json() == today
    assert daily_card_response.status_code == 200
    assert daily_card_response.json() == daily_card
    assert game_response.status_code == 200
    assert game_response.json() == game
    assert performance_response.status_code == 200
    assert performance_response.json() == performance