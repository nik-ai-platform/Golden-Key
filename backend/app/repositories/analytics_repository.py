from sqlalchemy.orm import Session

from app.models.analytics_feature import AnalyticsFeature
from app.models.game import Game
from app.models.nik_score import NikScore
from app.models.prediction_outcome import PredictionOutcome



def get_by_game(
    db: Session,
    game_id: int
):
    return (
        db.query(AnalyticsFeature)
        .filter(
            AnalyticsFeature.game_id == game_id
        )
        .first()
    )


def save(
    db: Session,
    analytics: AnalyticsFeature
):
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    return analytics


def get_evaluations(
    db: Session
):
    return (
        db.query(PredictionOutcome)
        .all()
    )


def get_sport_accuracy_rows(
    db: Session
):
    return (
        db.query(
            Game.sport,
            PredictionOutcome.prediction_correct
        )
        .join(PredictionOutcome, PredictionOutcome.game_id == Game.id)
        .all()
    )


def get_model_accuracy_rows(
    db: Session
):
    return (
        db.query(
            NikScore.model_version,
            PredictionOutcome.prediction_correct
        )
        .join(NikScore, NikScore.id == PredictionOutcome.prediction_id)
        .all()
    )


def get_evaluation_trend_rows(
    db: Session,
    *,
    team_id: int | None = None,
    sport: str | None = None,
    version: str | None = None,
):
    query = (
        db.query(
            Game.game_date,
            PredictionOutcome.prediction_correct,
            PredictionOutcome.predicted_confidence,
            Game.home_team_id,
            Game.away_team_id,
            Game.sport,
            NikScore.model_version,
        )
        .join(PredictionOutcome, PredictionOutcome.game_id == Game.id)
        .join(NikScore, NikScore.id == PredictionOutcome.prediction_id)
    )

    if team_id is not None:
        query = query.filter(
            (Game.home_team_id == team_id)
            |
            (Game.away_team_id == team_id)
        )

    if sport is not None:
        query = query.filter(Game.sport == sport)

    if version is not None:
        query = query.filter(
            NikScore.model_version == version
        )

    return query.order_by(Game.game_date.asc()).all()
