from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.api_contract import (
    GameDetailResponse,
    PerformanceResponse,
    SavedPicksResponse,
    TodayPredictionsResponse,
)
from app.services.v1_read_service import V1ReadService


router = APIRouter(
    prefix="/product",
    tags=["Product v1"],
)

service = V1ReadService()


@router.get(
    "/predictions/today",
    response_model=TodayPredictionsResponse,
)
def today_predictions(
    sport: str | None = None,
    include_passes: bool = False,
    db: Session = Depends(get_db),
):
    return service.get_today_predictions(
        db=db,
        sport=sport,
        include_passes=include_passes,
    )


@router.get(
    "/games/{game_id}",
    response_model=GameDetailResponse,
)
def game_detail(
    game_id: int,
    db: Session = Depends(get_db),
):
    try:
        return service.get_game_detail(
            db=db,
            game_id=game_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.get(
    "/me/saved-picks",
    response_model=SavedPicksResponse,
)
def saved_picks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_saved_picks(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/performance",
    response_model=PerformanceResponse,
)
def performance(
    db: Session = Depends(get_db),
):
    return service.get_performance(db=db)
