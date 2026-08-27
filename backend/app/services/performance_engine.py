from sqlalchemy.orm import Session

from app.models.prediction_result import (
    PredictionResult
)


class PerformanceEngine:

    def calculate_metrics(
        self,
        db: Session
    ):

        results = (

            db.query(
                PredictionResult
            )

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
