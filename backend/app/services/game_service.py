from sqlalchemy.orm import Session

from app.repositories import game_repository
from app.schemas.game import GameCreate, GameUpdate


def create_game(
    db: Session,
    game: GameCreate
):
    return game_repository.create_game(db, game)


def get_games(
    db: Session
):
    return game_repository.get_games(db)


def get_game_by_id(
    db: Session,
    game_id: int
):
    return game_repository.get_game_by_id(db, game_id)


def update_game(
    db: Session,
    db_game,
    game: GameUpdate
):
    return game_repository.update_game(db, db_game, game)


def delete_game(
    db: Session,
    db_game
):
    game_repository.delete_game(db, db_game)
