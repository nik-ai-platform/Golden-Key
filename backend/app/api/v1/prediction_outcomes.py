from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_viewer
from app.database.session import get_db
from app.services.prediction_outcome_service import PredictionOutcomeService


router = APIRouter(
    prefix="/predictions",
    tags=["Prediction Outcomes"],
    dependencies=[Depends(require_viewer)],
)


@router.get("/outcomes")
def list_prediction_outcomes(
    db: Session = Depends(get_db),
    limit: int = 100,
):
    service = PredictionOutcomeService()
    return service.list_outcomes(db, limit=limit)


@router.get("/outcomes/{prediction_id}")
def get_prediction_outcome(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    service = PredictionOutcomeService()
    outcome = service.get_outcome_by_prediction_id(db, prediction_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Prediction outcome not found")
    return outcome
