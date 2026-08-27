from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.npi_weight_profile import NPIWeightCreate, NPIWeightResponse
from app.services.npi_weight_profile_service import NPIWeightProfileService


router = APIRouter(
    prefix="/npi-weights",
    tags=["NPI Weights"],
)

service = NPIWeightProfileService()


@router.get(
    "/{sport}/{model_version}",
)
def get_profile(
    sport: str,
    model_version: str,
    db: Session = Depends(get_db),
):

    try:
        weights = service.get_profile(
            db=db,
            sport=sport,
            model_version=model_version,
        )
        return {
            "sport": sport.upper(),
            "model_version": model_version,
            "weights": weights,
            "total_weight": sum(weights.values()),
        }
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.put(
    "/{sport}/{model_version}",
    response_model=list[NPIWeightResponse],
)
def replace_profile(
    sport: str,
    model_version: str,
    weights: list[NPIWeightCreate],
    db: Session = Depends(get_db),
):

    mismatched = [
        weight
        for weight in weights
        if weight.sport.upper() != sport.upper()
        or weight.model_version != model_version
    ]
    if mismatched:
        raise HTTPException(
            status_code=400,
            detail="Profile items must match the requested sport and model version",
        )

    try:
        return service.create_profile(
            db=db,
            sport=sport,
            model_version=model_version,
            weights={
                weight.factor_name: weight.weight
                for weight in weights
            },
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post(
    "/{sport}/{source_version}/clone/{target_version}",
    response_model=list[NPIWeightResponse],
)
def clone_profile(
    sport: str,
    source_version: str,
    target_version: str,
    db: Session = Depends(get_db),
):

    try:
        return service.clone_profile(
            db=db,
            sport=sport,
            source_version=source_version,
            target_version=target_version,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
