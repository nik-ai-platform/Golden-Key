from datetime import datetime, timezone

from sqlalchemy.orm import Session, aliased

from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.user_prediction import UserPrediction


class V1ReadService:

    def get_today_predictions(
        self,
        db: Session,
        sport: str | None = None,
        include_passes: bool = False,
    ) -> dict:
        day_start = datetime.now(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None,
        )
        day_end = day_start.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        home_team = aliased(Team)
        away_team = aliased(Team)
        query = (
            db.query(Prediction, Game, home_team, away_team)
            .join(Game, Game.id == Prediction.game_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
            .filter(
                Game.game_date >= day_start,
                Game.game_date <= day_end,
            )
        )
        if sport:
            query = query.filter(Game.sport == sport.upper())
        if not include_passes:
            query = query.filter(Prediction.selection != "PASS")

        rows = query.order_by(
            Prediction.confidence_score.desc(),
            Prediction.npi_score.desc(),
        ).all()
        items = [
            self._prediction_item(prediction, game, home, away)
            for prediction, game, home, away in rows
        ]
        return {
            "sport": sport.upper() if sport else None,
            "count": len(items),
            "predictions": items,
        }

    def get_game_detail(
        self,
        db: Session,
        game_id: int,
    ) -> dict:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        home_team = (
            db.query(Team)
            .filter(Team.id == game.home_team_id)
            .first()
        )
        away_team = (
            db.query(Team)
            .filter(Team.id == game.away_team_id)
            .first()
        )
        prediction = (
            db.query(Prediction)
            .filter(Prediction.game_id == game_id)
            .order_by(Prediction.id.desc())
            .first()
        )
        return {
            "game_id": game.id,
            "sport": game.sport,
            "home_team": (
                home_team.name if home_team else str(game.home_team_id)
            ),
            "away_team": (
                away_team.name if away_team else str(game.away_team_id)
            ),
            "game_date": game.game_date.isoformat(),
            "prediction": (
                self._prediction_item(
                    prediction,
                    game,
                    home_team,
                    away_team,
                )
                if prediction
                else None
            ),
        }

    def get_saved_picks(
        self,
        db: Session,
        user_id: int,
    ) -> dict:
        rows = (
            db.query(UserPrediction, Prediction)
            .join(
                Prediction,
                Prediction.id == UserPrediction.prediction_id,
            )
            .filter(UserPrediction.user_id == user_id)
            .all()
        )
        picks = []
        for saved, prediction in rows:
            result = (
                db.query(PredictionResult)
                .filter(PredictionResult.prediction_id == prediction.id)
                .first()
            )
            picks.append(
                {
                    "saved_pick_id": saved.id,
                    "prediction_id": prediction.id,
                    "game_id": prediction.game_id,
                    "market": prediction.market,
                    "selection": prediction.selection,
                    "confidence_score": prediction.confidence_score,
                    "outcome": result.outcome if result else None,
                }
            )
        return {
            "count": len(picks),
            "picks": picks,
        }

    def get_performance(self, db: Session) -> dict:
        results = db.query(PredictionResult).all()
        wins = sum(row.outcome == "WIN" for row in results)
        losses = sum(row.outcome == "LOSS" for row in results)
        pushes = sum(row.outcome == "PUSH" for row in results)
        graded = wins + losses
        accuracy = wins / graded * 100 if graded else 0.0
        profit_loss = sum(float(row.profit_loss or 0) for row in results)
        return {
            "total_predictions": len(results),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "accuracy": round(accuracy, 2),
            "profit_loss": round(profit_loss, 2),
        }

    def _prediction_item(
        self,
        prediction: Prediction,
        game: Game,
        home_team: Team,
        away_team: Team,
    ) -> dict:
        return {
            "prediction_id": prediction.id,
            "game_id": game.id,
            "sport": game.sport,
            "home_team": home_team.name,
            "away_team": away_team.name,
            "game_date": game.game_date.isoformat(),
            "market": prediction.market,
            "selection": prediction.selection,
            "model_version": prediction.model_version,
            "npi_score": float(prediction.npi_score),
            "confidence_score": prediction.confidence_score,
            "simulation_probability": prediction.simulation_probability,
            "projected_edge": prediction.projected_edge,
            "risk_level": prediction.risk_level,
            "reasoning": prediction.reasoning,
        }
