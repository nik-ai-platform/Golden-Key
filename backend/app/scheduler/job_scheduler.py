import logging

from app.services.import_service import ImportService
from app.services.prediction_service import PredictionService


logger = logging.getLogger(__name__)


class JobScheduler:

    def __init__(self):

        self.import_service = ImportService()

        self.prediction_service = PredictionService()


    def run(
        self,
        db,
        sport="basketball_nba"
    ):

        logger.info(
            "Nik AI scheduled update started"
        )

        try:

            games = self.import_service.import_games(
                db,
                sport
            )

            logger.info(
                f"Imported {len(games)} games"
            )


            logger.info(
                "Scheduled update completed"
            )


            return games


        except Exception:

            logger.exception(
                "Scheduler failed"
            )

            return []
