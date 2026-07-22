import httpx

from app.core.config import settings
from app.providers.base import SportsDataProvider


SPORT_KEY_MAP = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "wnba": "basketball_wnba",
    "ncaab": "basketball_ncaab",
    "ncaaf": "americanfootball_ncaaf",
}


class OddsAPIProvider(SportsDataProvider):

    def __init__(self):
        self.client = httpx.Client(
            base_url=settings.ODDS_API_BASE_URL,
            timeout=30
        )

    def get_games(self, sport: str):
        normalized = sport.strip().lower()
        odds_api_sport = SPORT_KEY_MAP.get(normalized, normalized)

        response = self.client.get(
            f"/sports/{odds_api_sport}/odds",
            params={
                "apiKey": settings.ODDS_API_KEY,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american"
            }
        )

        response.raise_for_status()

        return response.json()

    def get_odds(self, sport: str):
        return self.get_games(sport)

    def get_scores(self, sport: str):
        return []