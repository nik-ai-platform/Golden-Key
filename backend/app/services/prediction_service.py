from sqlalchemy.orm import Session
from app.models.prediction_record import Prediction
from app.schemas.prediction import PredictionCreate


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

