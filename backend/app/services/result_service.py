from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.prediction_result import (
    PredictionResult
)


def record_result(
    db: Session,
    data
):

    result = PredictionResult(

        **data.model_dump()

    )

    db.add(result)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid prediction_id")

    db.refresh(result)

    return result


def get_results(
    db: Session
):

    return (

        db.query(
            PredictionResult
        )

        .all()

    )