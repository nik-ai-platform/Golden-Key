from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.end_to_end_prediction_service import (
    EndToEndPredictionService,
)


router = APIRouter(
    prefix="/system",
    tags=["System Integration"],
)

service = EndToEndPredictionService()


@router.post("/run/{sport}")
def run_sport(
    sport: str,
    db: Session = Depends(get_db),
):
    try:
        return service.run(
            db=db,
            sport=sport,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
