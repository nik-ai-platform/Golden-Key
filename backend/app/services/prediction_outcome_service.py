from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.nik_score import NikScore
from app.models.prediction_outcome import PredictionOutcome
from app.repositories import game_repository
from app.services.monitoring_service import MonitoringService


class PredictionOutcomeService:
    def __init__(self, monitor=None):
        self.monitor = monitor or MonitoringService()

    def _latest_prediction_for_game(self, db: Session, game_id: int):
        return (
            db.query(NikScore)
            .filter(NikScore.game_id == game_id)
            .order_by(NikScore.id.desc())
            .first()
        )

    def _winner_name(self, game: Game | None):
        if not game or game.winner_team_id is None:
            return None

        if game.home_team_id == game.winner_team_id and game.home_team:
            return game.home_team.name

        if game.away_team_id == game.winner_team_id and game.away_team:
            return game.away_team.name

        return None

    def _predicted_winner_name(self, prediction: NikScore):
        if prediction.recommendation:
            return prediction.recommendation
        return ""

    def _point_spread_error(self, game: Game, prediction: NikScore):
        if (
            game.home_score is None
            or game.away_score is None
            or prediction.home_score is None
            or prediction.away_score is None
        ):
            return None

        actual_margin = abs(float(game.home_score) - float(game.away_score))
        predicted_margin = abs(float(prediction.home_score) - float(prediction.away_score))
        return round(abs(predicted_margin - actual_margin), 2)

    def _serialize(self, outcome: PredictionOutcome):
        return {
            "id": outcome.id,
            "prediction_id": outcome.prediction_id,
            "game_id": outcome.game_id,
            "predicted_winner": outcome.predicted_winner,
            "actual_winner": outcome.actual_winner,
            "predicted_confidence": outcome.predicted_confidence,
            "prediction_correct": outcome.prediction_correct,
            "point_spread_error": outcome.point_spread_error,
            "created_at": outcome.created_at.isoformat() if outcome.created_at else None,
        }

    def evaluate_prediction(self, db: Session, prediction_id: int):
        existing = (
            db.query(PredictionOutcome)
            .filter(PredictionOutcome.prediction_id == prediction_id)
            .first()
        )
        if existing:
            return existing

        prediction = db.query(NikScore).filter(NikScore.id == prediction_id).first()
        if not prediction:
            return None

        game = game_repository.get_game_with_teams(db, prediction.game_id)
        if not game:
            return None

        actual_winner = self._winner_name(game)
        if not actual_winner:
            return None

        predicted_winner = self._predicted_winner_name(prediction)
        outcome = PredictionOutcome(
            prediction_id=prediction.id,
            game_id=game.id,
            predicted_winner=predicted_winner,
            actual_winner=actual_winner,
            predicted_confidence=prediction.confidence or 0.0,
            prediction_correct=(predicted_winner == actual_winner),
            point_spread_error=self._point_spread_error(game, prediction),
        )

        db.add(outcome)
        db.commit()
        db.refresh(outcome)

        self.monitor.log_scheduler(
            "Evaluated prediction outcome",
            prediction_id=outcome.prediction_id,
            game_id=outcome.game_id,
            correct=outcome.prediction_correct,
        )

        return outcome

    def evaluate_completed_games(self, db: Session, limit: int = 100):
        games = game_repository.get_completed_games(db, limit=limit)
        outcomes = []

        for game in games:
            prediction = self._latest_prediction_for_game(db, game.id)
            if not prediction:
                continue

            outcome = self.evaluate_prediction(db, prediction.id)
            if outcome:
                outcomes.append(outcome)

        return outcomes

    def list_outcomes(self, db: Session, limit: int = 100):
        return [
            self._serialize(outcome)
            for outcome in (
                db.query(PredictionOutcome)
                .order_by(PredictionOutcome.created_at.desc(), PredictionOutcome.id.desc())
                .limit(limit)
                .all()
            )
        ]

    def get_outcome_by_prediction_id(self, db: Session, prediction_id: int):
        outcome = (
            db.query(PredictionOutcome)
            .filter(PredictionOutcome.prediction_id == prediction_id)
            .first()
        )
        return self._serialize(outcome) if outcome else None

    def update_prediction_metrics(self, db: Session):
        outcomes = db.query(PredictionOutcome).all()
        total = len(outcomes)

        if total == 0:
            return {
                "winner_accuracy": 0,
                "confidence_accuracy": 0,
                "margin_error": 0,
                "total_outcomes": 0,
            }

        correct = sum(1 for outcome in outcomes if outcome.prediction_correct)
        confidence_alignment = sum(
            outcome.predicted_confidence if outcome.prediction_correct else (100 - outcome.predicted_confidence)
            for outcome in outcomes
            if outcome.predicted_confidence is not None
        )
        confidence_accuracy = round(confidence_alignment / total, 2)

        margin_errors = [
            outcome.point_spread_error
            for outcome in outcomes
            if outcome.point_spread_error is not None
        ]
        margin_error = round(sum(margin_errors) / len(margin_errors), 2) if margin_errors else 0

        return {
            "winner_accuracy": round(correct / total * 100, 2),
            "confidence_accuracy": confidence_accuracy,
            "margin_error": margin_error,
            "total_outcomes": total,
        }
