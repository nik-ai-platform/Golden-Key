from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.user_prediction import (
    UserPrediction
)


def save_prediction(
    db: Session,
    user_id: int,
    prediction_id: int
):

    existing = (
        db.query(UserPrediction)
        .filter(
            UserPrediction.user_id == user_id,
            UserPrediction.prediction_id == prediction_id,
        )
        .first()
    )

    if existing:
        return existing

    saved = UserPrediction(

        user_id=user_id,

        prediction_id=prediction_id

    )

    db.add(saved)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Request is idempotent: return existing save if a concurrent insert won.
        existing_after_rollback = (
            db.query(UserPrediction)
            .filter(
                UserPrediction.user_id == user_id,
                UserPrediction.prediction_id == prediction_id,
            )
            .first()
        )
        if existing_after_rollback:
            return existing_after_rollback
        raise HTTPException(status_code=400, detail="Invalid prediction_id")

    db.refresh(saved)

    return saved


def get_user_predictions(
    db: Session,
    user_id: int
):

    return (

        db.query(UserPrediction)

        .filter(
            UserPrediction.user_id ==
            user_id
        )

        .all()

    )


def remove_saved_prediction(
    db: Session,
    user_id: int,
    prediction_id: int,
) -> bool:
    saved = (
        db.query(UserPrediction)
        .filter(
            UserPrediction.user_id == user_id,
            UserPrediction.prediction_id == prediction_id,
        )
        .first()
    )

    if saved is None:
        return False

    db.delete(saved)
    db.commit()
    return True