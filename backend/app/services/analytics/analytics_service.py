from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from time import perf_counter

from app.models.feature_snapshot import FeatureSnapshot
from app.models.model_performance import ModelPerformance
from app.repositories import analytics_repository
from app.repositories import prediction_repository
from app.services.cache_service import cache_service
from app.services.calibration_service import CalibrationService
from app.services.feature_importance_service import FeatureImportanceService
from app.services.model_evaluation_service import ModelEvaluationService
from app.services.model_version_service import ModelVersionService
from app.services.monitoring_service import MonitoringService
from app.services.analytics.confidence_service import (
    ConfidenceService
)
from app.services.prediction_outcome_service import PredictionOutcomeService


class AnalyticsService:
    """
    Handles accuracy and dashboard analytics.
    """


    def __init__(
        self,
        confidence_service=None,
        outcome_service=None,
        calibration_service=None,
        feature_importance_service=None,
    ):

        self.confidence = (
            confidence_service or ConfidenceService()
        )
        self.outcomes = (
            outcome_service or PredictionOutcomeService()
        )
        self.calibration = (
            calibration_service or CalibrationService()
        )
        self.feature_importance = (
            feature_importance_service or FeatureImportanceService()
        )
        self.model_evaluation = ModelEvaluationService()
        self.model_versions = ModelVersionService()
        self.monitor = MonitoringService()


    def calculate_accuracy(
        self,
        db: Session | None = None,
        evaluations=None
    ):

        if evaluations is None:

            if db is None:
                return 0

            evaluations = (
                analytics_repository.get_evaluations(
                    db
                )
            )

        if not evaluations:
            return 0

        correct = sum(
            1
            for evaluation in evaluations
            if evaluation.correct
        )

        return round(
            (
                correct /
                len(evaluations)
            )
            * 100,
            2
        )


    def overall_accuracy(
        self,
        db: Session
    ):
        return self.calculate_accuracy(db=db)


    def sport_accuracy(
        self,
        db: Session
    ):

        rows = (
            analytics_repository.get_sport_accuracy_rows(
                db
            )
        )

        results = {}

        for sport, correct in rows:

            if sport not in results:
                results[sport] = {
                    "total": 0,
                    "correct": 0
                }

            results[sport]["total"] += 1

            if correct:
                results[sport]["correct"] += 1

        for sport, data in results.items():

            data["accuracy"] = round(
                (
                    data["correct"] /
                    data["total"]
                )
                * 100,
                2
            )

        return results


    def model_accuracy(
        self,
        db: Session
    ):

        rows = (
            analytics_repository.get_model_accuracy_rows(
                db
            )
        )

        results = {}

        for version, correct in rows:

            if version not in results:
                results[version] = {
                    "total": 0,
                    "correct": 0
                }

            results[version]["total"] += 1

            if correct:
                results[version]["correct"] += 1

        for version, data in results.items():

            data["accuracy"] = round(
                (
                    data["correct"] /
                    data["total"]
                )
                * 100,
                2
            )

        return results


    def dashboard_summary(
        self,
        db: Session,
        limit: int = 10
    ):
        return self.dashboard_statistics(db=db, limit=limit)


    def dashboard_statistics(
        self,
        db: Session,
        limit: int = 10
    ):
        cache_key = f"analytics:dashboard-statistics:{limit}"
        return cache_service.get_or_set(
            cache_key,
            lambda: self._dashboard_statistics_uncached(db, limit),
            ttl_seconds=90,
        )


    def _dashboard_statistics_uncached(
        self,
        db: Session,
        limit: int,
    ):
        started_at = perf_counter()
        marks: dict[str, float] = {}

        def _mark(name: str):
            marks[name] = round((perf_counter() - started_at) * 1000, 2)

        recent_predictions = (
            prediction_repository.get_recent_snapshots(
                db,
                limit
            )
        )
        _mark("recent_predictions")
        recent_predictions_payload = [
            {
                "id": row.id,
                "game_id": row.game_id,
                "model_version": row.model_version,
                "prediction": row.prediction,
                "confidence": row.confidence,
                "home_score": row.home_score,
                "away_score": row.away_score,
            }
            for row in recent_predictions
        ]

        model_comparison = None
        model_rows = self._safe_model_rows(db)
        _mark("model_rows")
        if len(model_rows) == 2:
            current_metric = {
                "accuracy": round(float(model_rows[0].accuracy or 0.0), 2),
                "calibration": 0.0,
                "average_confidence": round(float(model_rows[0].average_confidence or 0.0), 2),
                "predictions": int(model_rows[0].total_predictions or 0),
            }
            candidate_metric = {
                "accuracy": round(float(model_rows[1].accuracy or 0.0), 2),
                "calibration": 0.0,
                "average_confidence": round(float(model_rows[1].average_confidence or 0.0), 2),
                "predictions": int(model_rows[1].total_predictions or 0),
            }
            model_comparison = self.model_evaluation.compare_models(
                current_metric,
                candidate_metric,
            ).model_dump()

        current_model = self.model_versions.get_current_version()
        candidate_versions = [
            row.model_version for row in model_rows if row.model_version != current_model
        ]
        best_candidate = candidate_versions[0] if candidate_versions else None
        training_samples = self._safe_training_sample_count(db)
        _mark("training_samples")

        overall_accuracy = self.calculate_accuracy(db=db)
        _mark("overall_accuracy")
        sport_accuracy = self.sport_accuracy(db)
        _mark("sport_accuracy")
        model_accuracy = self.model_accuracy(db)
        _mark("model_accuracy")
        confidence_buckets = self.confidence.confidence_buckets(db)
        _mark("confidence_buckets")
        calibration = self.calibration.calculate_calibration(db=db)
        _mark("calibration")
        feature_importance = self.feature_importance.historical_importance(db)
        _mark("feature_importance")
        prediction_outcomes = self.outcomes.update_prediction_metrics(db)
        _mark("prediction_outcomes")

        self.monitor.log_scheduler(
            "Dashboard analytics timings",
            total_ms=round((perf_counter() - started_at) * 1000, 2),
            **marks,
        )

        return {
            "overall_accuracy": overall_accuracy,
            "sport_accuracy": sport_accuracy,
            "model_accuracy": model_accuracy,
            "confidence_buckets": confidence_buckets,
            "calibration": calibration,
            "feature_importance": feature_importance,
            "model_comparison": model_comparison,
            "model_learning": {
                "current_model": current_model,
                "training_samples": training_samples,
                "candidate_models": len(candidate_versions),
                "best_candidate": best_candidate,
            },
            "prediction_outcomes": prediction_outcomes,
            "recent_predictions": recent_predictions_payload,
        }


    def _safe_model_rows(self, db: Session):
        try:
            return (
                db.query(ModelPerformance)
                .order_by(ModelPerformance.accuracy.desc())
                .limit(2)
                .all()
            )
        except SQLAlchemyError:
            db.rollback()
            return []


    def _safe_training_sample_count(self, db: Session) -> int:
        try:
            return (
                db.query(FeatureSnapshot.prediction_id)
                .distinct()
                .count()
            )
        except SQLAlchemyError:
            db.rollback()
            return 0
