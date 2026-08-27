from sqlalchemy.orm import Session

from app.models.backtest_result import BacktestResult
from app.repositories import game_repository
from app.repositories import prediction_repository
from app.services.analytics.analytics_service import (
    AnalyticsService
)


class BacktestService:
    """
    Handles replay, backtests, and model comparisons.
    """


    def __init__(
        self,
        analytics_service=None,
    ):
        self.analytics = (
            analytics_service or AnalyticsService()
        )


    def calculate_accuracy(
        self,
        evaluations
    ):
        return self.analytics.calculate_accuracy(
            evaluations=evaluations
        )


    def create_result(
        self,
        db: Session,
        model_version,
        evaluations,
        sport="unknown",
    ):

        accuracy = (
            self.calculate_accuracy(
                evaluations
            )
        )

        average_confidence = 0

        if evaluations:
            average_confidence = round(
                sum(
                    item.confidence
                    for item in evaluations
                )
                /
                len(evaluations),
                2
            )

        result = BacktestResult(

            model_version=model_version,

            sport=sport,

            market="summary",

            outcome="PUSH",

            total_predictions=len(
                evaluations
            ),

            correct_predictions=sum(
                1
                for item in evaluations
                if item.correct
            ),

            accuracy=accuracy,

            average_confidence=average_confidence

        )

        db.add(result)

        db.commit()

        db.refresh(result)

        return result


    def get_snapshots(
        self,
        db: Session,
        limit: int = 100
    ):
        return (
            prediction_repository.get_snapshots(
                db,
                limit
            )
        )


    def evaluate_snapshot(
        self,
        db: Session,
        snapshot,
        actual_winner
    ):

        correct = (
            snapshot.prediction
            ==
            str(actual_winner)
        )

        evaluation = (
            prediction_repository.create_evaluation(
                db,
                snapshot_id=snapshot.id,
                correct=correct,
                predicted_team=snapshot.prediction,
                actual_winner=actual_winner,
                confidence=snapshot.confidence
            )
        )

        return evaluation


    def replay(
        self,
        db: Session,
        snapshots
    ):

        results = []

        for snapshot in snapshots:

            game = (
                game_repository.get_game(
                    db,
                    snapshot.game_id
                )
            )

            if not game or not game.winner_team_id:
                continue

            result = (
                self.evaluate_snapshot(
                    db,
                    snapshot,
                    game.winner_team_id
                )
            )

            results.append(result)

        return results


    def run_backtest(
        self,
        db: Session,
        limit: int = 100
    ):

        snapshots = (
            prediction_repository.get_snapshots_with_completed_games(
                db,
                limit
            )
        )

        evaluations = self.replay(
            db,
            snapshots
        )

        version_groups = {}

        for snapshot in snapshots:

            if snapshot.model_version not in version_groups:
                version_groups[snapshot.model_version] = []

            version_groups[snapshot.model_version].append(snapshot.id)

        return {
            "snapshots_processed": len(snapshots),
            "evaluations_created": len(evaluations),
            "model_versions": list(version_groups.keys()),
        }


    def rank_models(
        self,
        models
    ):

        if not models:
            return []

        return sorted(
            models,
            key=lambda model:
            model.accuracy,
            reverse=True
        )


    def best_model(
        self,
        models
    ):

        ranked = (
            self.rank_models(models)
        )

        if not ranked:

            return None

        return ranked[0]


    def model_comparisons(
        self,
        models
    ):

        ranked = self.rank_models(models)

        return {
            "ranked_models": ranked,
            "best_model": self.best_model(models)
        }
