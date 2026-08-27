from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.completed_game_settlement_service import (
    CompletedGameSettlementService,
)
from app.services.result_settlement_service import ResultSettlementService


router = APIRouter(
    prefix="/settlement",
    tags=["Settlement"],
)

game_service = ResultSettlementService()
completed_service = CompletedGameSettlementService()


@router.post("/game/{game_id}")
def settle_game(
    game_id: int,
    db: Session = Depends(get_db),
):
    try:
        return game_service.settle_game(
            db=db,
            game_id=game_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post("/completed")
def settle_completed_games(
    db: Session = Depends(get_db),
):
    return completed_service.settle_completed_games(db=db)


@router.post("/completed/{sport}")
def settle_completed_sport(
    sport: str,
    db: Session = Depends(get_db),
):
    return completed_service.settle_completed_games(
        db=db,
        sport=sport,
    )
