from datetime import UTC, datetime

from app.providers.base import SportsDataProvider


class MockSportsDataProvider(SportsDataProvider):

    def get_games(self, sport: str):
        """
        Development-only provider that returns a single sample game.
        Replace this with a real API client implementation.
        """
        now = datetime.now(UTC)
        return [
            {
                "external_id": "mock-game-001",
                "sport": "basketball",
                "league": "NBA",
                "season": now.year,
                "home_team": "Lakers",
                "away_team": "Celtics",
                "game_date": now.isoformat(),
                "status": "scheduled",
            }
        ]

    def get_odds(self, sport: str):
        return []

    def get_scores(self, sport: str):
        return []
