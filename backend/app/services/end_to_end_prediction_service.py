from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.game import Game
from app.services.prediction_engine import PredictionEngine
from app.services.real_data_import_service import RealDataImportService


class EndToEndPredictionService:

    def __init__(self) -> None:
        self.importer = RealDataImportService()
        self.prediction_engine = PredictionEngine()

    def run(
        self,
        db: Session,
        sport: str,
    ) -> dict:
        sport = sport.upper()
        import_result = self.importer.import_sport(
            db=db,
            sport=sport,
        )

        today = datetime.utcnow().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        tomorrow = today + timedelta(days=1)
        games = (
            db.query(Game)
            .filter(
                Game.sport == sport,
                Game.game_date >= today,
                Game.game_date < tomorrow,
            )
            .all()
        )

        predictions = []
        failures = []

        for game in games:
            try:
                prediction = self.prediction_engine.analyze_game(
                    db=db,
                    game_id=game.id,
                    persist=True,
                )
                predictions.append(
                    {
                        "game_id": game.id,
                        "prediction_id": prediction.id,
                        "model_version": prediction.model_version,
                        "selection": prediction.selection,
                        "npi_score": prediction.npi_score,
                    }
                )
            except Exception as error:
                db.rollback()
                failures.append(
                    {
                        "game_id": game.id,
                        "error": str(error),
                    }
                )

        return {
            "sport": sport,
            "import": import_result,
            "predictions_created": len(predictions),
            "predictions": predictions,
            "failures": failures,
        }
