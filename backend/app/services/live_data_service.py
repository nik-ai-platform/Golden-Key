import logging


logger = logging.getLogger(__name__)


class LiveDataService:

    """
    Handles importing live sports data.
    """

    def __init__(self):
        pass


    def fetch_games(self, sport: str | None = None):

        logger.info(
            "Fetching live games"
        )

        # API connection will be added here

        return []


    def update_games(self):

        games = self.fetch_games()

        logger.info(
            f"Received {len(games)} games"
        )

        return games
