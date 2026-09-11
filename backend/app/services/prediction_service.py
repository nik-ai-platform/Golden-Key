from sqlalchemy.orm import Session
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.schemas.prediction import PredictionCreate
from app.services.ncaaf_rule_intelligence_service import (
    record_rule_intelligence_for_prediction,
)


def create_prediction(
    db: Session,
    prediction: PredictionCreate,
):
    db_prediction = Prediction(
        **prediction.model_dump()
    )

    db.add(db_prediction)
    db.flush()
    odds_snapshot = (
        db.get(Odds, db_prediction.odds_snapshot_id)
        if db_prediction.odds_snapshot_id is not None
        else None
    )
    record_rule_intelligence_for_prediction(
        db=db,
        prediction=db_prediction,
        odds_snapshot=odds_snapshot,
    )
    db.commit()
    db.refresh(db_prediction)

    return db_prediction


def get_predictions(
    db: Session,
):
    return (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .all()
    )

