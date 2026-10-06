from sqlalchemy.orm import Session

from app.models.prediction_result import (
    PredictionResult
)
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.services.performance_scope import regular_season_games


class PerformanceEngine:

    def calculate_metrics(
        self,
        db: Session
    ):

        results = (

            db.query(
                PredictionResult
            )
            .join(Prediction, Prediction.id == PredictionResult.prediction_id)
            .join(Game, Game.id == Prediction.game_id)
            .filter(regular_season_games())
            .all()

        )

        total = len(results)

        if total == 0:

            return {

                "total_predictions": 0,

                "accuracy": 0,

                "wins": 0,

                "losses": 0

            }

        wins = len(

            [

                value for value in results

                if value.outcome == "WIN"

            ]

        )

        losses = len(

            [

                value for value in results

                if value.outcome == "LOSS"

            ]

        )

        accuracy = (

            wins / total

        ) * 100

        return {

            "total_predictions":

                total,

            "wins":

                wins,

            "losses":

                losses,

            "accuracy":

                round(
                    accuracy,
                    2
                )

        }
