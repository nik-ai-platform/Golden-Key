from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_analyst
from app.database.session import get_db
from app.services.prediction_history_service import PredictionHistoryService

router = APIRouter(prefix="/prediction-history", tags=["Prediction History"], dependencies=[Depends(require_analyst)])


@router.post("")
def save_prediction_history(payload: dict, db: Session = Depends(get_db)):
    service = PredictionHistoryService()
    return service.record_prediction(db, payload)


@router.get("")
def list_prediction_history(db: Session = Depends(get_db)):
    service = PredictionHistoryService()
    return service.list_history(db, limit=20)


@router.get("/export")
def export_prediction_history(db: Session = Depends(get_db)):
    service = PredictionHistoryService()
    return service.export_history(db)


@router.delete("")
def clear_prediction_history(db: Session = Depends(get_db), _=Depends(require_admin)):
    service = PredictionHistoryService()
    return service.clear_history(db)
