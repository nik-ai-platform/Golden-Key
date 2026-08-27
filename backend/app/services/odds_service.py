from sqlalchemy.orm import Session

from app.models.odds import Odds
from app.repositories import odds_repository
from app.services.monitoring_service import MonitoringService


class OddsService:

    """
    Handles sportsbook odds processing.
    """

    def __init__(
        self,
        monitor=None,
    ):
        self.monitor = monitor or MonitoringService()

    def save_odds(
        self,
        db: Session,
        odds_data: dict
    ):

        odds = Odds(
            **odds_data
        )

        return odds_repository.save_odds(db, odds)


    def get_game_odds(
        self,
        db: Session,
        game_id: int
    ):
        return odds_repository.get_game_odds(db, game_id)


    def extract_market_values(
        self,
        bookmaker: dict
    ):

        spread_home = None
        spread_away = None
        moneyline_home = None
        moneyline_away = None
        total = None

        for market in bookmaker.get(
            "markets",
            []
        ):
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

        return (
            spread_home,
            spread_away,
            moneyline_home,
            moneyline_away,
            total
        )


def create_odds_snapshot(
    db: Session,
    game_id: int,
    bookmaker: dict,
    odds_service=None,
    monitor=None,
):

    service = odds_service or OddsService()
    monitor = monitor or service.monitor

    (
        spread_home,
        spread_away,
        moneyline_home,
        moneyline_away,
        total
    ) = service.extract_market_values(
        bookmaker
    )

    odds = Odds(
        game_id=game_id,

        sportsbook=bookmaker.get(
            "title"
        ),

        spread_home=spread_home,

        spread_away=spread_away,

        moneyline_home=moneyline_home,

        moneyline_away=moneyline_away,

        total=total
    )

    monitor.log_import(
        "Saved odds snapshot",
        game_id=game_id,
        sportsbook=bookmaker.get("title"),
    )

    return odds_repository.save_odds(db, odds)


def get_latest_odds(
    db: Session,
    game_id: int
):

    return odds_repository.get_latest_odds(db, game_id)


def get_odds_history(
    db: Session,
    game_id: int
):

    return odds_repository.get_odds_history(db, game_id)
