from datetime import datetime
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.services.v1_read_service as v1_read_service
from app.database.base import Base
from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.services.prediction_engine import PredictionEngine
from app.services.result_settlement_service import ResultSettlementService
from app.services.v1_read_service import V1ReadService


def test_prediction_generation_settlement_and_performance_lifecycle():
    database_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=database_engine)
    connection = database_engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)

    try:
        home_team = Team(name="Home Team", sport="NCAAF", league="NCAAF")
        away_team = Team(name="Away Team", sport="NCAAF", league="NCAAF")
        db.add_all([home_team, away_team])
        db.flush()

        game = Game(
            sport="NCAAF",
            league="NCAAF",
            season=2026,
            provider_game_id="prediction-lifecycle-integration",
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=datetime(2026, 9, 5, 19, 30),
        )
        db.add(game)
        db.flush()

        odds = Odds(
            game_id=game.id,
            sportsbook="Integration Sportsbook",
            spread_home=-7.5,
            spread_away=7.5,
            moneyline_home=-280,
            moneyline_away=230,
            total=52.5,
        )
        db.add(odds)
        db.commit()

        prediction_engine = PredictionEngine()
        prediction_engine.model_runtime = MagicMock()
        prediction_engine.model_runtime.resolve.side_effect = ValueError(
            "No production model configured for sport: NCAAF"
        )
        prediction_engine.npi_engine = MagicMock()
        prediction_engine.npi_engine.calculate.return_value = {
            "npi_score": 110,
            "factors": [],
        }
        prediction_engine.simulation_engine = MagicMock()
        prediction_engine.simulation_engine.simulate.return_value = {
            "win_probability": 62,
            "runs": 10000,
            "average_margin": 4.0,
        }
        prediction_engine.ai_engine = MagicMock()
        prediction_engine.ai_engine.generate_analysis.return_value = {
            "engine_version": "integration-test",
            "summary": "Lifecycle integration test",
            "explanation": "Lifecycle integration test",
        }

        generated = prediction_engine.analyze_markets(
            db=db,
            game_id=game.id,
            persist=True,
        )
        predictions = (
            db.query(Prediction)
            .filter(Prediction.game_id == game.id)
            .all()
        )

        assert len(generated) == len(predictions) == 3
        assert {prediction.market for prediction in predictions} == {
            "spread",
            "moneyline",
            "total",
        }
        assert all(
            prediction.id is not None
            and prediction.odds_snapshot_id == odds.id
            and prediction.sportsbook == odds.sportsbook
            and prediction.odds_observed_at == odds.created_at
            and prediction.model_version
            for prediction in predictions
        )
        by_market = {prediction.market: prediction for prediction in predictions}
        assert by_market["spread"].line_value is not None
        assert by_market["spread"].american_odds is not None
        assert by_market["moneyline"].american_odds is not None
        assert by_market["total"].line_value is not None
        assert by_market["total"].american_odds is not None

        game.home_score = 31
        game.away_score = 21
        game.status = "final"
        db.commit()

        settlement_service = ResultSettlementService()
        first_settlement = settlement_service.settle_game(db, game.id)
        first_results = db.query(PredictionResult).all()

        assert first_settlement["settled"] == 3
        assert len(first_results) == 3
        assert {result.prediction_id for result in first_results} == {
            prediction.id for prediction in predictions
        }

        second_settlement = settlement_service.settle_game(db, game.id)

        assert second_settlement["settled"] == 0
        assert db.query(PredictionResult).count() == 3

        performance = V1ReadService().get_performance(db)

        assert performance["total_predictions"] == 3
        assert sum(
            item["settled"] for item in performance["market_performance"]
        ) == 3
        assert {item["name"] for item in performance["market_performance"]} == {
            "spread",
            "moneyline",
            "total",
        }
        assert not hasattr(v1_read_service, "NikScore")
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        database_engine.dispose()
