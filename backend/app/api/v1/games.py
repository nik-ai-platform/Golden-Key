from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst, require_viewer
from app.database.session import get_db
from app.schemas.game import GameCreate, GameResponse, GameUpdate
from app.services.cache_service import cache_service
from app.services import game_service


router = APIRouter(
    prefix="/games",
    tags=["Games"],
    dependencies=[Depends(require_viewer)],
)


@router.post("/", response_model=GameResponse)
def create_game(
    game: GameCreate,
    db: Session = Depends(get_db),
    _=Depends(require_analyst),
):
    try:
        created = game_service.create_game(db, game)
        cache_service.clear_prefix("games:")
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[GameResponse])
def get_games(
    db: Session = Depends(get_db)
):
    return cache_service.get_or_set("games:list", lambda: game_service.get_games(db), ttl_seconds=60)


@router.get("/{id}", response_model=GameResponse)
def get_game(
    id: int,
    db: Session = Depends(get_db)
):
    game = cache_service.get_or_set(f"games:{id}", lambda: game_service.get_game(db, id), ttl_seconds=60)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return game


@router.put("/{id}", response_model=GameResponse)
def update_game(
    id: int,
    game: GameUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_analyst),
):
    updated = game_service.update_game(db, id, game)

    if not updated:
        raise HTTPException(status_code=404, detail="Game not found")

    cache_service.clear_prefix("games:")
    return updated


@router.delete("/{id}")
def delete_game(
    id: int,
    db: Session = Depends(get_db),
    _=Depends(require_analyst),
):
    deleted = game_service.delete_game(db, id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Game not found")

    cache_service.clear_prefix("games:")
    return {"detail": "Game deleted"}
