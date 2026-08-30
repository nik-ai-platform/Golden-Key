import requests

from app.core.config import settings
from app.services.monitoring_service import MonitoringService
from app.services.sport_mapping_service import SportMappingService


class LiveDataService:
    """
    Handles importing live sports data from The Odds API.
    """

    BASE_URL = "https://api.the-odds-api.com/v4/sports"

    def update_game_state(self, game_data):
        if not game_data:
            return None

        if game_data.get("game_id") is None:
            return None

        return {
            "game_id": game_data.get("game_id"),
            "home_score": game_data.get("home_score", 0),
            "away_score": game_data.get("away_score", 0),
            "quarter_period": game_data.get("quarter_period", "Q1"),
            "clock": game_data.get("clock", "00:00"),
            "possession": game_data.get("possession", "HOME"),
            "momentum_score": game_data.get("momentum_score", 0),
        }

    def get_live_games(self):
        return []

    def process_event(self, event):
        if not event:
            return None

        return {
            "event_type": event.get("event_type", "GAME_STATE_CHANGE"),
            "game_id": event.get("game_id"),
            "message": event.get("message", "Game state updated"),
        }

    def __init__(
        self,
        monitor=None,
        sport_mapping=None,
    ):
        self.monitor = monitor or MonitoringService()
        self.sport_mapping = sport_mapping or SportMappingService()


    def fetch_games(
        self,
        sport: str
    ):

        provider_sport = self.sport_mapping.provider_key(sport)

        self.monitor.log_import(
            "Fetching games",
            sport=sport,
            provider_sport=provider_sport,
        )

        response = requests.get(
            f"{self.BASE_URL}/{provider_sport}/odds",
            params={
                "apiKey": settings.ODDS_API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
            },
            timeout=15,
        )

        response.raise_for_status()

        return response.json()


    def update_games(
        self,
        sport: str
    ):

        games = self.fetch_games(sport)

        self.monitor.log_import(
            "Received games",
            count=len(games),
            sport=sport
        )

        return games
