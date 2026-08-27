from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.prediction_evaluation import (
    PredictionEvaluation
)
from app.models.prediction_snapshot import (
    PredictionSnapshot
)


def get_snapshots(
    db: Session,
    limit: int = 100
):
    return (
        db.query(
            PredictionSnapshot
        )
        .limit(limit)
        .all()
    )


def get_recent_snapshots(
    db: Session,
    limit: int = 10
):
    return (
        db.query(
            PredictionSnapshot
        )
        .order_by(
            PredictionSnapshot.id.desc()
        )
        .limit(limit)
        .all()
    )


def get_latest_snapshot_for_game(
    db: Session,
    game_id: int
):
    return (
        db.query(PredictionSnapshot)
        .filter(
            PredictionSnapshot.game_id == game_id
        )
        .order_by(
            PredictionSnapshot.id.desc()
        )
        .first()
    )


def get_snapshots_with_completed_games(
    db: Session,
    limit: int = 100
):
    return (
        db.query(PredictionSnapshot)
        .join(
            Game,
            Game.id == PredictionSnapshot.game_id
        )
        .filter(
            Game.winner_team_id.isnot(None)
        )
        .order_by(
            PredictionSnapshot.id.desc()
        )
        .limit(limit)
        .all()
    )


def create_evaluation(
    db: Session,
    *,
    snapshot_id: int,
    correct: bool,
    predicted_team,
    actual_winner,
    confidence: float
):
    evaluation = PredictionEvaluation(
        snapshot_id=snapshot_id,
        correct=correct,
        predicted_team=predicted_team,
        actual_winner=actual_winner,
        confidence=confidence,
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    return evaluation
