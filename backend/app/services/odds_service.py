import logging

from sqlalchemy.orm import Session

from app.models.odds import Odds


logger = logging.getLogger(__name__)


class OddsService:

    def __init__(self, db: Session | None = None):
        self.db = db

    def update_odds(self, sport: str | None = None):
        if self.db is None or sport is None:
            logger.info("OddsService.update_odds skipped: missing db or sport.")
            return []

        logger.info("OddsService.update_odds called for sport=%s", sport)
        return []


def create_odds_snapshot(
    db: Session,
    game_id: int,
    bookmaker_data: dict
):
    sportsbook = bookmaker_data.get(
        "name",
        bookmaker_data.get("title", bookmaker_data.get("key"))
    )

    spread_home = bookmaker_data.get("spread_home")
    spread_away = bookmaker_data.get("spread_away")
    moneyline_home = bookmaker_data.get("moneyline_home")
    moneyline_away = bookmaker_data.get("moneyline_away")
    total = bookmaker_data.get("total")

    if spread_home is None and bookmaker_data.get("markets"):
        for market in bookmaker_data.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            if key == "h2h" and len(outcomes) >= 2:
                moneyline_home = outcomes[0].get("price")
                moneyline_away = outcomes[1].get("price")

            if key == "spreads" and outcomes:
                spread_home = outcomes[0].get("point")
                if len(outcomes) > 1:
                    spread_away = outcomes[1].get("point")

            if key == "totals" and outcomes:
                total = outcomes[0].get("point")

    odds = Odds(
        game_id=game_id,
        sportsbook=sportsbook,
        spread_home=spread_home,
        spread_away=spread_away,
        moneyline_home=moneyline_home,
        moneyline_away=moneyline_away,
        total=total
    )

    db.add(odds)
    db.commit()
    db.refresh(odds)

    return odds


def get_latest_odds(
    db: Session,
    game_id: int
):
    return (
        db.query(Odds)
        .filter(Odds.game_id == game_id)
        .order_by(Odds.created_at.desc(), Odds.id.desc())
        .first()
    )


def get_odds_history(
    db: Session,
    game_id: int
):
    return (
        db.query(Odds)
        .filter(Odds.game_id == game_id)
        .order_by(Odds.created_at.asc(), Odds.id.asc())
        .all()
    )