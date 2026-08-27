from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.auth.dependencies import require_viewer
from app.database.session import get_db
from app.services.odds_service import get_latest_odds, get_odds_history


router = APIRouter(
    prefix="/odds",
    tags=["Odds"],
    dependencies=[Depends(require_viewer)],
)


@router.get("/{game_id}/latest")
def latest_odds(
    game_id: int,
    db: Session = Depends(get_db)
):
    return get_latest_odds(db, game_id)


@router.get("/{game_id}/history")
def odds_history(
    game_id: int,
    db: Session = Depends(get_db)
):
    return get_odds_history(db, game_id)
