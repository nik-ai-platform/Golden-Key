from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.game import GameCreate, GameResponse, GameUpdate
from app.services import game_service


router = APIRouter(
    prefix="/games",
    tags=["Games"]
)


@router.post("/", response_model=GameResponse)
def create_game(
    game: GameCreate,
    db: Session = Depends(get_db)
):
    try:
        return game_service.create_game(db, game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[GameResponse])
def get_games(
    db: Session = Depends(get_db)
):
    return game_service.get_games(db)


@router.get("/{id}", response_model=GameResponse)
def get_game(
    id: int,
    db: Session = Depends(get_db)
):
    game = game_service.get_game(db, id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return game


@router.put("/{id}", response_model=GameResponse)
def update_game(
    id: int,
    game: GameUpdate,
    db: Session = Depends(get_db)
):
    updated = game_service.update_game(db, id, game)

    if not updated:
        raise HTTPException(status_code=404, detail="Game not found")

    return updated


@router.delete("/{id}")
def delete_game(
    id: int,
    db: Session = Depends(get_db)
):
    deleted = game_service.delete_game(db, id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Game not found")

    return {"detail": "Game deleted"}
