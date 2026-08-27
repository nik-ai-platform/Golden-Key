from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.model_rollback import ModelRollbackRequest
from app.services.production_model_service import ProductionModelService
from app.services.model_rollback_service import ModelRollbackService


router = APIRouter(
    prefix="/model-runtime",
    tags=["Model Runtime"],
)

production_service = ProductionModelService()
rollback_service = ModelRollbackService()


@router.get("/production/{sport}")
def get_production_model(
    sport: str,
    db: Session = Depends(get_db),
):

    normalized_sport = sport.upper()

    try:
        version = production_service.get_active_version(
            db=db,
            sport=normalized_sport,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return {
        "sport": normalized_sport,
        "model_version": version,
        "status": "production",
    }


@router.post("/rollback")
def rollback_model(
    request: ModelRollbackRequest,
    db: Session = Depends(get_db),
):

    return rollback_service.rollback(
        db=db,
        sport=request.sport.upper(),
        target_version=request.target_version,
        approved_by=request.approved_by,
        reason=request.reason,
    )
