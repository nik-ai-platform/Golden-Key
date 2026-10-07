from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.auth.dependencies import get_current_user
from app.auth.persistent_user import resolve_persistent_user_id
from app.auth.schemas import AuthUser
from app.database.session import get_db
from app.core.premium import require_premium_user
from app.models.game import Game
from app.schemas.launch_preview import SlatePreviewGame, SlatePreviewResponse
from app.schemas.api_contract import (
    DailyCardResponse,
    GameDetailResponse,
    PerformanceResponse,
    SavedPicksResponse,
    TodayPredictionsResponse,
    UpcomingPredictionsResponse,
)
from app.services.v1_read_service import V1ReadService


router = APIRouter(
    prefix="/product",
    tags=["Product v1"],
)

service = V1ReadService()


@router.get("/preview", response_model=SlatePreviewResponse)
def slate_preview(
    sport: str | None = Query(default=None, max_length=16),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
):
    now = datetime.now(UTC).replace(tzinfo=None)
    query = db.query(Game).options(joinedload(Game.home_team), joinedload(Game.away_team)).filter(
        Game.game_date >= now.replace(hour=0, minute=0, second=0, microsecond=0),
        Game.game_date < now + timedelta(days=7),
    )
    if sport:
        query = query.filter(Game.sport == sport.upper())
    games = query.order_by(Game.game_date, Game.id).limit(100).all()
    preview = [
        SlatePreviewGame(
            game_id=game.id, sport=game.sport, league=game.league,
            home_team=game.home_team.name, away_team=game.away_team.name,
            start_time=game.game_date, status=game.status,
        )
        for game in games
    ]
    return SlatePreviewResponse(sport=sport.upper() if sport else None, count=len(preview), games=preview)


@router.get(
    "/daily-card",
    response_model=DailyCardResponse,
    dependencies=[Depends(require_premium_user)],
)
def daily_card(
    sport: str | None = None,
    db: Session = Depends(get_db),
):
    return service.get_daily_card(db=db, sport=sport)


@router.get(
    "/predictions/today",
    response_model=TodayPredictionsResponse,
    dependencies=[Depends(require_premium_user)],
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
    "/predictions/upcoming",
    response_model=UpcomingPredictionsResponse,
    dependencies=[Depends(require_premium_user)],
)
def upcoming_predictions(
    sport: str | None = None,
    include_passes: bool = False,
    db: Session = Depends(get_db),
):
    return service.get_upcoming_predictions(
        db=db,
        sport=sport,
        include_passes=include_passes,
    )


@router.get(
    "/games/{game_id}",
    response_model=GameDetailResponse,
    dependencies=[Depends(require_premium_user)],
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
    current_user: AuthUser = Depends(require_premium_user),
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
    dependencies=[Depends(require_premium_user)],
)
def performance(
    db: Session = Depends(get_db),
):
    return service.get_performance(db=db)


@router.get("/performance-intelligence")
def get_performance_intelligence(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_premium_user),
):
    return service.get_performance_intelligence(
        db,
        days=days,
    )
