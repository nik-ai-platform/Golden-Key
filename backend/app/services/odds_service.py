from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.odds import Odds
from app.repositories import odds_repository
from app.services.monitoring_service import MonitoringService


class NoCompleteOddsSnapshotError(ValueError):
    pass


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
        bookmaker: dict,
        home_team: str,
        away_team: str,
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

            if key == "h2h":
                for outcome in outcomes:
                    if outcome.get("name") == home_team:
                        moneyline_home = outcome.get("price")
                    elif outcome.get("name") == away_team:
                        moneyline_away = outcome.get("price")

            if key == "spreads":
                for outcome in outcomes:
                    if outcome.get("name") == home_team:
                        spread_home = outcome.get("point")
                    elif outcome.get("name") == away_team:
                        spread_away = outcome.get("point")

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
    game = db.get(Game, game_id)
    if game is None:
        raise ValueError(f"Game {game_id} not found")

    (
        spread_home,
        spread_away,
        moneyline_home,
        moneyline_away,
        total
    ) = service.extract_market_values(
        bookmaker,
        game.home_team.name,
        game.away_team.name,
    )

    required_values = (
        spread_home,
        spread_away,
        moneyline_home,
        moneyline_away,
        total,
    )
    if any(value is None for value in required_values):
        monitor.log_import(
            "Skipped incomplete odds snapshot",
            game_id=game_id,
            sportsbook=bookmaker.get("title"),
        )
        return None

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
