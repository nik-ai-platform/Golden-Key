from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.nik_score import NikScore

from app.services.nik_power_engine import NikPowerEngine


class PredictionService:

    def __init__(self):

        self.engine = NikPowerEngine()

    def generate_prediction(
        self,
        db: Session,
        game_id: int
    ):

        game = (
            db.query(Game)
            .filter(
                Game.id == game_id
            )
            .first()
        )

        if not game:
            return None

        home_performance = (
            game.home_team.performance
        )

        away_performance = (
            game.away_team.performance
        )

        home_score = (
            self.engine.calculate_team_score(
                home_performance,
                None
            )
        )

        away_score = (
            self.engine.calculate_team_score(
                away_performance,
                None
            )
        )

        recommendation = (
            game.home_team.name
            if home_score > away_score
            else game.away_team.name
        )

        confidence = round(
            abs(home_score - away_score),
            2
        )

        if confidence <= 55:
            confidence_level = "LOW"

        elif confidence <= 75:
            confidence_level = "MODERATE"

        elif confidence <= 90:
            confidence_level = "STRONG"

        else:
            confidence_level = "ELITE"

        prediction = NikScore(

            game_id=game.id,

            home_score=home_score,

            away_score=away_score,

            confidence=confidence,

            confidence_level=confidence_level,

            model_version="NPI-v1",

            recommendation=recommendation

        )

        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        return prediction