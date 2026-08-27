from sqlalchemy.orm import Session

from app.models.odds import Odds


def save_odds(
    db: Session,
    odds: Odds
):
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