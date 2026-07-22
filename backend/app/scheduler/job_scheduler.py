from app.services.prediction_service import PredictionService


import logging


logger = logging.getLogger(__name__)


class JobScheduler:

    def __init__(self):

        self.prediction_service = PredictionService()


    def run(self):

        logger.info(
            "Nik AI scheduled update started"
        )

        try:

            # Future pipeline:
            #
            # 1. Import live games
            # 2. Update odds
            # 3. Generate features
            # 4. Generate predictions

            logger.info(
                "Prediction pipeline ready"
            )

        except Exception as e:

            logger.exception(e)
