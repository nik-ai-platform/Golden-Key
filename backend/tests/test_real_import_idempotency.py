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
    existing = SimpleNamespace(id=41, model_version="NPI-4.1")
    game_query = MagicMock()
    game_query.filter.return_value.first.return_value = game
    prediction_query = MagicMock()
    prediction_query.filter.return_value.first.return_value = existing
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

    assert result is existing
    engine.npi_engine.calculate.assert_not_called()
