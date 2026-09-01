from sqlalchemy.orm import Session
from app.models.prediction_record import Prediction
from app.schemas.prediction import PredictionCreate


class PredictionService:
    pass


def create_prediction(
    db: Session,
    prediction: PredictionCreate,
):
    db_prediction = Prediction(
        **prediction.model_dump()
    )

    db.add(db_prediction)
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


def get_prediction_by_id(
    db: Session,
    prediction_id: int,
):
    return (
        db.query(Prediction)
        .filter(
            Prediction.id == prediction_id
        )
        .first()
    )

