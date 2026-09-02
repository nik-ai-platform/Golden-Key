from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.persistent_user import resolve_persistent_user_id
from app.auth.schemas import AuthUser
from app.database.session import get_db
from app.schemas.api_contract import (
    DailyCardResponse,
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
    "/daily-card",
    response_model=DailyCardResponse,
    dependencies=[Depends(get_current_user)],
)
def daily_card(
    sport: str | None = None,
    db: Session = Depends(get_db),
):
    return service.get_daily_card(db=db, sport=sport)


@router.get(
    "/predictions/today",
    response_model=TodayPredictionsResponse,
    dependencies=[Depends(get_current_user)],
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
    dependencies=[Depends(get_current_user)],
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
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_persistent_user_id(
        db,
        current_user,
    )

    return service.get_saved_picks(
        db=db,
        user_id=user_id,
    )


@router.get(
    "/performance",
    response_model=PerformanceResponse,
    dependencies=[Depends(get_current_user)],
)
def performance(
    db: Session = Depends(get_db),
):
    return service.get_performance(db=db)


@router.get("/performance-intelligence")
def get_performance_intelligence(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    return service.get_performance_intelligence(
        db,
        days=days,
    )
