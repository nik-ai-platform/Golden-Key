from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.odds import Odds

SNAPSHOT_FIELDS = (
    "spread_home", "spread_away", "moneyline_home", "moneyline_away", "total",
    "spread_home_price", "spread_away_price", "total_over_price", "total_under_price",
)


def save_odds(
    db: Session,
    odds: Odds
):
    game = (
        db.query(Game).filter(Game.id == odds.game_id)
        .populate_existing().with_for_update().first()
    )
    if game is None:
        raise ValueError(f"Game {odds.game_id} not found")
    latest = (
        db.query(Odds)
        .filter(Odds.game_id == odds.game_id, Odds.sportsbook == odds.sportsbook)
        .order_by(Odds.id.desc()).populate_existing().first()
    )
    if latest is not None and all(
        getattr(latest, name) == getattr(odds, name) for name in SNAPSHOT_FIELDS
    ):
        db.commit()
        return latest
    db.add(odds)
    db.commit()
    db.refresh(odds)
    return odds


def get_game_odds(
    db: Session,
    game_id: int
):
    return (
        db.query(Odds)
        .filter(
            Odds.game_id == game_id
        )
        .all()
    )


def get_latest_odds(
    db: Session,
    game_id: int
):
    return (
        db.query(Odds)
        .filter(
            Odds.game_id == game_id
        )
        .order_by(
            Odds.id.desc()
        )
        .first()
    )


def get_odds_history(
    db: Session,
    game_id: int
):
    return (
        db.query(Odds)
        .filter(
            Odds.game_id == game_id
        )
        .order_by(
            Odds.id.asc()
        )
        .all()
    )