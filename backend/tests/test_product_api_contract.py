from datetime import datetime
from types import SimpleNamespace

from app.schemas.api_contract import (
    PerformanceResponse,
    TodayPredictionItem,
    TodayPredictionsResponse,
)
from app.services.v1_read_service import V1ReadService


def test_today_prediction_contract():
    item = TodayPredictionItem(
        prediction_id=1,
        game_id=10,
        sport="NBA",
        home_team="Boston Celtics",
        away_team="New York Knicks",
        game_date="2026-08-08T20:00:00",
        market="spread",
        selection="HOME",
        model_version="NPI-4.0",
        npi_score=145.0,
        confidence_score=78.0,
        simulation_probability=61.0,
        projected_edge=5.2,
        risk_level="medium",
        reasoning="Test",
    )
    response = TodayPredictionsResponse(
        sport="NBA",
        slate_date="2026-08-08",
        count=1,
        predictions=[item],
    )

    assert response.count == 1
    assert response.slate_date == "2026-08-08"
    assert response.predictions[0].home_team == "Boston Celtics"
    assert response.predictions[0].model_version == "NPI-4.0"


def test_product_prediction_serializes_odds_provenance_as_utc():
    prediction = SimpleNamespace(
        id=1,
        market="moneyline",
        selection="HOME",
        line_value=None,
        american_odds=130,
        sportsbook="DraftKings",
        odds_observed_at=datetime(2026, 9, 1, 20, 32),
        model_version="NPI-4.0",
        npi_score=145.0,
        confidence_score=78.0,
        simulation_probability=61.0,
        projected_edge=5.2,
        risk_level="medium",
        reasoning="Test",
    )
    game = SimpleNamespace(id=10, sport="NFL", game_date=datetime(2026, 9, 2))
    home_team = SimpleNamespace(name="Seattle Seahawks")
    away_team = SimpleNamespace(name="New England Patriots")

    item = TodayPredictionItem.model_validate(
        V1ReadService()._prediction_item(
            prediction,
            game,
            home_team,
            away_team,
        )
    )

    assert item.sportsbook == "DraftKings"
    assert item.odds_observed_at == "2026-09-01T20:32:00Z"


def test_performance_contract():
    result = PerformanceResponse(
        total_predictions=100,
        wins=55,
        losses=40,
        pushes=5,
        accuracy=57.89,
        profit_loss=325.50,
    )

    assert result.wins == 55
    assert result.pushes == 5
