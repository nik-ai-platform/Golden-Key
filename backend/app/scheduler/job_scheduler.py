from datetime import UTC, datetime, timedelta
from time import perf_counter

from app.repositories import game_repository

from app.services.import_service import ImportService
from app.services.model_training_service import ModelTrainingService
from app.services.monitoring_service import MonitoringService
from app.services.performance_metrics_service import performance_metrics
from app.services.prediction_outcome_service import PredictionOutcomeService
from app.services.prediction_service import PredictionService
from app.services.training_dataset_service import TrainingDatasetService


class JobScheduler:

    def __init__(
        self,
        import_service=None,
        prediction_service=None,
        outcome_service=None,
        dataset_service=None,
        training_service=None,
        monitor=None,
    ):

        self.import_service = (
            import_service or ImportService()
        )

        self.prediction_service = (
            prediction_service or PredictionService()
        )

        self.outcome_service = (
            outcome_service or PredictionOutcomeService()
        )

        self.dataset_service = (
            dataset_service or TrainingDatasetService()
        )

        self.training_service = (
            training_service or ModelTrainingService(dataset_service=self.dataset_service)
        )

        self.monitor = monitor or MonitoringService()


    def run(
        self,
        db,
        sport="basketball_nba"
    ):

        self.monitor.log_scheduler(
            "Nik AI pipeline started",
            sport=sport
        )


        stage_results = []

        games = self._run_stage(
            "import_games",
            sport,
            stage_results,
            lambda: self.import_service.import_games(db, sport),
            default_value=[],
        )

        predictions = self._run_stage(
            "generate_predictions",
            sport,
            stage_results,
            lambda: self._generate_predictions(db, games),
            default_value=[],
        )

        outcomes = self._run_stage(
            "evaluate_outcomes",
            sport,
            stage_results,
            lambda: self.outcome_service.evaluate_completed_games(db),
            default_value=[],
        )
        self.monitor.log_scheduler(
            "Evaluated completed games",
            count=len(outcomes),
            sport=sport,
        )

        metrics = self._run_stage(
            "refresh_analytics",
            sport,
            stage_results,
            lambda: self.outcome_service.update_prediction_metrics(db),
            default_value={},
        )
        self.monitor.log_scheduler(
            "Updated prediction metrics",
            sport=sport,
            **metrics,
        )

        self._run_stage(
            "update_training_dataset",
            sport,
            stage_results,
            lambda: self._refresh_training_dataset(db),
            default_value={"records": 0, "valid": False},
        )

        candidate_reports = self._run_stage(
            "evaluate_candidate_models",
            sport,
            stage_results,
            lambda: self.training_service.evaluate_candidate_models(games=[]),
            default_value=[],
        )
        self.monitor.log_scheduler(
            "Evaluated candidate models",
            sport=sport,
            candidates=len(candidate_reports),
        )

        self.monitor.log_scheduler(
            "Nik AI pipeline completed",
            sport=sport,
            stages=len(stage_results),
        )

        return predictions


    def _generate_predictions(self, db, games):
        predictions = []
        team_ids = {
            getattr(game, "home_team_id", None)
            for game in games
        } | {
            getattr(game, "away_team_id", None)
            for game in games
        }
        team_ids.discard(None)

        recent_games_map = {}
        if team_ids:
            recent_games_map = game_repository.get_recent_games_for_teams(
                db,
                list(team_ids),
                limit=10,
            )

        for game in games:
            try:
                prediction = self.prediction_service.generate_prediction(
                    db,
                    game.id,
                    preloaded_recent_games=recent_games_map,
                )
            except TypeError:
                prediction = self.prediction_service.generate_prediction(
                    db,
                    game.id,
                )
            predictions.append(prediction)

        self.monitor.log_scheduler(
            "Generated predictions",
            count=len(predictions),
        )
        return predictions


    def _refresh_training_dataset(self, db):
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=30)

        dataset = self.dataset_service.build_dataset(
            start_date=start_date,
            end_date=end_date,
            db=db,
        )

        validation = self.dataset_service.validate_dataset(dataset)
        self.monitor.log_scheduler(
            "Refreshed training dataset",
            records=validation["records"],
            valid=validation["valid"],
        )
        return validation


    def _run_stage(
        self,
        stage_name,
        sport,
        stage_results,
        operation,
        default_value,
    ):
        started = perf_counter()
        try:
            result = operation()
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            stage_results.append(
                {
                    "stage": stage_name,
                    "status": "ok",
                    "elapsed_ms": elapsed_ms,
                }
            )

            self.monitor.log_scheduler(
                "Scheduler stage completed",
                stage=stage_name,
                sport=sport,
                elapsed_ms=elapsed_ms,
            )
            performance_metrics.record_scheduler_stage(
                stage_name,
                elapsed_ms,
                success=True,
            )
            return result
        except Exception as error:
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            stage_results.append(
                {
                    "stage": stage_name,
                    "status": "failed",
                    "elapsed_ms": elapsed_ms,
                }
            )
            self.monitor.log_exception(
                "Scheduler stage failed",
                stage=stage_name,
                sport=sport,
                elapsed_ms=elapsed_ms,
                error=error,
            )
            performance_metrics.record_scheduler_stage(
                stage_name,
                elapsed_ms,
                success=False,
            )
            return default_value
