from app.models.game import Game
from app.models.backtest_result import BacktestResult
from app.models.nik_score import NikScore
from app.models.prediction_outcome import PredictionOutcome
from sqlalchemy import case, func
from app.services.sport_mapping_service import NBA_PRESEASON


def regular_season_games():
    return Game.league != NBA_PRESEASON


def regular_backtest_history(query):
    return query.join(Game, Game.id == BacktestResult.game_id).filter(regular_season_games())


def regular_model_metrics(db):
    # Stored ModelPerformance aggregates have no game provenance.
    return (
        db.query(
            NikScore.model_version.label("model_version"),
            (func.avg(case((PredictionOutcome.prediction_correct.is_(True), 100.0), else_=0.0))).label("accuracy"),
            func.avg(PredictionOutcome.predicted_confidence).label("average_confidence"),
            func.count(PredictionOutcome.id).label("total_predictions"),
        )
        .select_from(PredictionOutcome)
        .join(NikScore, NikScore.id == PredictionOutcome.prediction_id)
        .join(Game, Game.id == PredictionOutcome.game_id)
        .filter(regular_season_games())
        .group_by(NikScore.model_version)
    )
