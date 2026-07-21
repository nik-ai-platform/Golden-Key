from sqlalchemy.orm import Session

from app.schemas.game import GameCreate, GameUpdate
from app.repositories import game_repository
from app.repositories import team_repository


def create_game(
    db: Session,
    game: GameCreate
):

    if game.home_team_id == game.away_team_id:
        raise ValueError(
            "Home team and away team cannot be the same"
        )

    home_team = team_repository.get_team(
        db,
        game.home_team_id
    )

    away_team = team_repository.get_team(
        db,
        game.away_team_id
    )

    if not home_team or not away_team:
        raise ValueError(
            "Team does not exist"
        )

    return game_repository.create_game(
        db,
        game
    )


def get_games(
    db: Session
):

    return game_repository.get_games(db)


def get_game(
    db: Session,
    game_id: int
):

    return game_repository.get_game_by_id(
        db,
        game_id
    )


def update_game(
    db: Session,
    game_id: int,
    game_data: GameUpdate
):

    db_game = get_game(
        db,
        game_id
    )

    if not db_game:
        return None

    return game_repository.update_game(
        db,
        db_game,
        game_data
    )


def delete_game(
    db: Session,
    game_id: int
):

    db_game = get_game(
        db,
        game_id
    )

    if not db_game:
        return None

    return game_repository.delete_game(
        db,
        db_game
    )
