from app.services.daily_prediction_pipeline import (
    DailyPredictionPipeline,
)
from app.services.game_importer import (
    GameImporter,
)
from app.services.odds_importer import (
    OddsImporter,
)
from app.services.sports_data_client import (
    SportsDataClient,
)


class DailyJob:

    def __init__(self):

        self.client = SportsDataClient()

        self.game_importer = GameImporter()

        self.odds_importer = OddsImporter()

        self.pipeline = DailyPredictionPipeline()

    def execute(
        self,
        db,
    ):

        sports = [
            "NFL",
            "NBA",
            "NCAAF",
            "NCAAB",
            "WNBA",
        ]

        status = {}

        for sport in sports:
            try:
                games = self.client.get_games(sport)

                self.game_importer.import_games(db, games)

                odds = self.client.get_odds(sport)

                self.odds_importer.import_odds(db, odds)

                status[sport] = "imported"
            except Exception as error:
                status[sport] = f"failed: {error}"

        try:
            pipeline_result = self.pipeline.run(db)
            status["predictions_created"] = pipeline_result.get("games_processed", 0)
        except Exception as error:
            status["predictions_created"] = 0
            status["pipeline"] = f"failed: {error}"

        return status