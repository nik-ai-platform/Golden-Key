from datetime import datetime

from sqlalchemy.orm import Session

from app.models.game import Game

from app.services.prediction_engine import (
    PredictionEngine
)


class DailyPredictionPipeline:

    VERSION = "PIPELINE-1.0"

    def __init__(self):

        self.prediction_engine = (
            PredictionEngine()
        )

    def run(
        self,
        db: Session
    ):

        start_time = datetime.utcnow()

        results = []

        games = self.get_pending_games(
            db
        )

        for game in games:

            try:

                prediction = (
                    self.prediction_engine
                    .analyze_game(
                        db,
                        game.id
                    )
                )

                results.append(
                    {
                        "game_id": game.id,

                        "status": "success",

                        "prediction_id":
                            prediction.id
                    }
                )

            except Exception as error:

                results.append(
                    {
                        "game_id": game.id,

                        "status": "failed",

                        "error": str(error)
                    }
                )

        return {

            "pipeline_version":
                self.VERSION,

            "started":
                start_time,

            "completed":
                datetime.utcnow(),

            "games_processed":
                len(games),

            "results":
                results
        }

    def get_pending_games(
        self,
        db: Session
    ):

        query = db.query(Game)

        if hasattr(Game, "status"):
            query = query.filter(
                Game.status == "scheduled"
            )

        return (

            query

            .all()

        )
