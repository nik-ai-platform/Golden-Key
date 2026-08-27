from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.model_bootstrap_service import ModelBootstrapService


router = APIRouter(
    prefix="/model-bootstrap",
    tags=["Model Bootstrap"],
)

service = ModelBootstrapService()


@router.post("/all")
def bootstrap_all_models(
    db: Session = Depends(get_db),
):
    return service.bootstrap_all(db=db)


@router.post("/{sport}")
def bootstrap_model(
    sport: str,
    db: Session = Depends(get_db),
):
    try:
        return service.bootstrap_sport(
            db=db,
            sport=sport,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
