from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.daily_prediction_pipeline import (
    DailyPredictionPipeline
)

router = APIRouter(
    prefix="/pipeline",
    tags=["Pipeline"]
)

pipeline = DailyPredictionPipeline()


@router.post("/run")
def run_pipeline(
    db: Session = Depends(get_db)
):

    return pipeline.run(
        db
    )
