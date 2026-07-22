import logging

from app.services.import_service import ImportService
from app.services.odds_service import OddsService
from app.services.feature_generator import FeatureGenerator
from app.services.prediction_service import PredictionService


logger = logging.getLogger(__name__)


class JobScheduler:

    def __init__(self):

        self.import_service = ImportService()

        self.odds_service = OddsService()

        self.feature_generator = FeatureGenerator()

        self.prediction_service = PredictionService()


    def run(self):

        logger.info(
            "Starting scheduled update..."
        )

        try:

            self.import_service.run()

            self.odds_service.update_odds()

            self.feature_generator.generate_features()

            logger.info(
                "Scheduled update completed."
            )

        except Exception as e:

            logger.exception(e)
