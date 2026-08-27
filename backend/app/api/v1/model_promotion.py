from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.model_promotion import ModelPromotionRequest
from app.services.model_promotion_service import ModelPromotionService


router = APIRouter(
    prefix="/models",
    tags=["Model Promotion"],
)

service = ModelPromotionService()


@router.get("/evaluate/{sport}/{model_version}")
def evaluate_model(
    sport: str,
    model_version: str,
    db: Session = Depends(get_db),
):

    return service.evaluate_candidate(
        db=db,
        model_version=model_version,
        sport=sport,
    )


@router.post("/promote")
def promote_model(
    request: ModelPromotionRequest,
    db: Session = Depends(get_db),
):

    return service.promote(
        db=db,
        model_version=request.model_version,
        sport=request.sport,
        approved_by=request.approved_by,
        notes=request.notes,
    )
