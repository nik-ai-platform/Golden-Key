from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.game_importer import GameImporter
from app.services.odds_importer import OddsImporter
from app.services.prediction_engine import PredictionEngine


def test_game_import_returns_existing_provider_game():
    existing = SimpleNamespace(id=17)
    query = MagicMock()
    query.filter.return_value.first.return_value = existing
    db = MagicMock()
    db.query.return_value = query

    result = GameImporter().import_games(
        db=db,
        games_data=[
            {
                "id": "provider-game-1",
                "home_team_id": 1,
                "away_team_id": 2,
                "sport": "NBA",
            }
        ],
    )

    assert result == [existing]
    db.add.assert_not_called()


def test_odds_import_updates_existing_sportsbook_row():
    existing = SimpleNamespace(
        spread_home=-3.0,
        spread_away=3.0,
        moneyline_home=-150,
        moneyline_away=130,
        total=220.0,
    )
    query = MagicMock()
    query.filter.return_value.first.return_value = existing
    db = MagicMock()
    db.query.return_value = query

    result = OddsImporter().import_odds(
        db=db,
        odds_data=[
            {
                "game_id": 17,
                "sportsbook": "Test Book",
                "spread_home": -4.5,
                "spread_away": 4.5,
                "moneyline_home": -180,
                "moneyline_away": 155,
                "total": 224.5,
            }
        ],
    )

    assert result == [existing]
    assert existing.spread_home == -4.5
    assert existing.moneyline_away == 155
    assert existing.total == 224.5
    db.add.assert_not_called()
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(existing)


def test_prediction_engine_returns_existing_production_prediction():
    game = SimpleNamespace(id=17, sport="NBA")
    existing = [
        SimpleNamespace(id=41, model_version="NPI-4.1", market="spread"),
        SimpleNamespace(id=42, model_version="NPI-4.1", market="moneyline"),
        SimpleNamespace(id=43, model_version="NPI-4.1", market="total"),
    ]
    game_query = MagicMock()
    game_query.filter.return_value.first.return_value = game
    prediction_query = MagicMock()
    prediction_query.filter.return_value.all.return_value = existing
    db = MagicMock()
    db.query.side_effect = [game_query, prediction_query]

    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.return_value = {
        "model_version": "NPI-4.1",
    }
    engine.npi_engine = MagicMock()

    result = engine.analyze_game(
        db=db,
        game_id=17,
        persist=True,
    )

    assert result is existing[0]
    engine.npi_engine.calculate.assert_not_called()


def test_prediction_engine_uses_default_version_without_production_model():
    game = SimpleNamespace(id=17, sport="WNBA")
    odds = SimpleNamespace(
        id=23,
        sportsbook="Test Sportsbook",
        created_at=datetime.now(timezone.utc),
        spread_home=-4.5,
        spread_away=4.5,
        moneyline_home=-180,
        moneyline_away=155,
        total=164.5,
    )
    game_query = MagicMock()
    game_query.filter.return_value.first.return_value = game
    odds_query = MagicMock()
    odds_query.filter.return_value.order_by.return_value.first.return_value = odds
    db = MagicMock()
    db.query.side_effect = [game_query, odds_query]

    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.side_effect = ValueError(
        "No production model configured for sport: WNBA"
    )
    engine.npi_engine = MagicMock()
    engine.npi_engine.calculate.return_value = {
        "npi_score": 100,
        "factors": [],
    }
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.return_value = {
        "win_probability": 60,
        "runs": 10000,
        "average_margin": 2.5,
    }
    engine.ai_engine = MagicMock()
    engine.ai_engine.generate_analysis.return_value = {
        "explanation": "Test analysis",
    }

    result = engine.analyze_game(
        db=db,
        game_id=17,
        persist=False,
    )

    assert result.model_version == "NPI-4.0"
    assert result.npi_score == 100


def test_prediction_engine_builds_three_independent_market_decisions():
    odds = SimpleNamespace(
        spread_home=-9.5,
        spread_away=9.5,
        moneyline_home=-470,
        moneyline_away=340,
        total=173.5,
    )
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.side_effect = [
        {
            "win_probability": 60,
            "runs": 10000,
            "average_margin": 3.0,
        },
        {
            "win_probability": 45,
            "runs": 10000,
            "average_margin": -1.5,
        },
    ]
    spread_npi = {
        "npi_score": 77.25,
        "factors": [],
    }

    specifications = engine._market_specifications(
        sport="WNBA",
        odds=odds,
        spread_npi=spread_npi,
    )

    assert [item["market"] for item in specifications] == [
        "spread",
        "moneyline",
        "total",
    ]
    assert len({item["npi_score"] for item in specifications}) == 3
    assert specifications[0]["selection"] == "HOME"
    assert specifications[0]["line_value"] == -9.5
    assert specifications[1]["selection"] == "AWAY"
    assert specifications[1]["american_odds"] == 340
    assert specifications[2]["selection"] == "UNDER"
    assert specifications[2]["line_value"] == 173.5
