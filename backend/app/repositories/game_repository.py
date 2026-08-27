from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.game import Game
from app.models.team import Team
from app.schemas.game import GameCreate, GameUpdate


def create_game(
    db: Session,
    game: GameCreate
):
    db_game = Game(
        **game.model_dump()
    )

    db.add(db_game)
    db.commit()
    db.refresh(db_game)

    return db_game


def get_games(
    db: Session
):
    return db.query(Game).all()


def get_games_with_teams(
    db: Session,
    limit: int = 100,
):
    return (
        db.query(Game)
        .options(
            joinedload(Game.home_team),
            joinedload(Game.away_team),
        )
        .order_by(Game.game_date.desc())
        .limit(limit)
        .all()
    )


def get_game_by_id(
    db: Session,
    game_id: int
):
    return db.query(Game).filter(Game.id == game_id).first()


def get_game(
    db: Session,
    game_id: int
):
    return get_game_by_id(
        db,
        game_id
    )


def get_game_with_teams(
    db: Session,
    game_id: int
):
    home_loader = joinedload(Game.home_team)
    away_loader = joinedload(Game.away_team)

    if hasattr(home_loader, "joinedload"):
        home_loader = home_loader.joinedload(Team.performance)

    if hasattr(away_loader, "joinedload"):
        away_loader = away_loader.joinedload(Team.performance)

    return (
        db.query(Game)
        .options(
            home_loader,
            away_loader,
        )
        .filter(
            Game.id == game_id
        )
        .first()
    )


def get_recent_games_for_team(
    db: Session,
    team_id: int,
    limit: int = 5
):
    return (
        db.query(Game)
        .filter(
            (Game.home_team_id == team_id)
            |
            (Game.away_team_id == team_id)
        )
        .order_by(
            Game.game_date.desc()
        )
        .limit(limit)
        .all()
    )


def get_recent_games_for_teams(
    db: Session,
    team_ids: list[int],
    limit: int = 10,
):
    if not team_ids:
        return {}

    rows = (
        db.query(Game)
        .filter(
            (Game.home_team_id.in_(team_ids))
            |
            (Game.away_team_id.in_(team_ids))
        )
        .order_by(Game.game_date.desc())
        .all()
    )

    grouped = {team_id: [] for team_id in team_ids}

    for game in rows:
        touched = []
        if game.home_team_id in grouped:
            touched.append(game.home_team_id)
        if game.away_team_id in grouped and game.away_team_id != game.home_team_id:
            touched.append(game.away_team_id)

        for team_id in touched:
            if len(grouped[team_id]) < limit:
                grouped[team_id].append(game)

    return grouped


def get_completed_games(
    db: Session,
    limit: int = 100
):
    return (
        db.query(Game)
        .filter(
            Game.winner_team_id.isnot(None)
        )
        .order_by(
            Game.game_date.desc()
        )
        .limit(limit)
        .all()
    )


def update_game(
    db: Session,
    db_game: Game,
    game: GameUpdate
):
    update_data = game.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_game, field, value)

    db.commit()
    db.refresh(db_game)

    return db_game


def delete_game(
    db: Session,
    db_game: Game
):
    db.delete(db_game)
    db.commit()

    return db_game
