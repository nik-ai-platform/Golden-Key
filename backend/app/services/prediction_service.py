from sqlalchemy.orm import Session
from time import perf_counter

from app.core.constants import HIGH_CONFIDENCE
from app.core.constants import LOW_CONFIDENCE
from app.core.constants import MODERATE_CONFIDENCE
from app.core.exceptions import PredictionException
from app.models.prediction.registry import ModelRegistry
from app.models.nik_score import NikScore
from app.repositories import game_repository

from app.services.confidence_service import ConfidenceService
from app.services.calibration_service import CalibrationService
from app.services.historical_performance_service import (
    HistoricalPerformanceService
)
from app.services.monitoring_service import MonitoringService
from app.services.prediction_feature_service import PredictionFeatureService
from app.services.prediction_snapshot_service import (
    PredictionSnapshotService
)
from app.services.performance_metrics_service import performance_metrics
from app.services.model_version_service import ModelVersionService
from app.services.market_intelligence_service import MarketIntelligenceService
from app.services.validation_service import (
    ValidationService
)
from app.models.prediction_record import Prediction
from app.schemas.prediction import PredictionCreate


class PredictionService:

    def __init__(
        self,
        engine=None,
        historical_service=None,
        feature_service=None,
        confidence_service=None,
        calibration_service=None,
        explanation_service=None,
        snapshot_service=None,
        version_service=None,
        validation_service=None,
        model_registry=None,
        market_intelligence_service=None,
        monitor=None,
    ):

        # Kept for backwards-compatible constructor signatures.
        self.engine = engine

        self.historical_service = (
            historical_service or HistoricalPerformanceService()
        )

        self.feature_service = (
            feature_service or PredictionFeatureService()
        )

        self.confidence_service = (
            confidence_service or ConfidenceService()
        )

        self.calibration_service = (
            calibration_service or CalibrationService()
        )

        # Kept for backwards-compatible constructor signatures.
        self.explanation_service = explanation_service

        self.snapshot_service = (
            snapshot_service or PredictionSnapshotService()
        )

        self.version_service = (
            version_service or ModelVersionService()
        )

        self.validation_service = (
            validation_service or ValidationService()
        )

        self.model_registry = (
            model_registry
            or ModelRegistry()
        )

        self.market_intelligence_service = (
            market_intelligence_service or MarketIntelligenceService()
        )

        self.monitor = monitor or MonitoringService()

    def calculate_historical_features(
        self,
        db,
        team_id
    ):

        games = (
            self.historical_service.get_recent_games(
                db,
                team_id,
                10
            )
        )


        return (
            self.historical_service.build_team_profile(
                games,
                team_id
            )
        )

    def generate_prediction(
        self,
        db: Session,
        game_id: int,
        preloaded_recent_games: dict[int, list] | None = None,
    ):
        started_at = perf_counter()
        try:

            game = (
                game_repository.get_game_with_teams(
                    db,
                    game_id
                )
            )

            if not game:
                return None

            if not self.validation_service.validate_game(game):

                raise PredictionException(
                    "Invalid game data"
                )

            home_performance = (
                game.home_team.performance
            )

            away_performance = (
                game.away_team.performance
            )

            home_features = self.feature_service.calculate_team_features(
                home_performance
            )

            away_features = self.feature_service.calculate_team_features(
                away_performance
            )

            if preloaded_recent_games is not None:
                home_games = preloaded_recent_games.get(game.home_team.id, [])
                away_games = preloaded_recent_games.get(game.away_team.id, [])
                home_history = self.feature_service.calculate_historical_features_from_games(
                    home_games,
                    game.home_team.id,
                )
                away_history = self.feature_service.calculate_historical_features_from_games(
                    away_games,
                    game.away_team.id,
                )
            else:
                home_history = (
                    self.feature_service.calculate_historical_features(
                        db,
                        game.home_team.id
                    )
                )

                away_history = (
                    self.feature_service.calculate_historical_features(
                        db,
                        game.away_team.id
                    )
                )

            home_features.update(
                home_history
            )

            away_features.update(
                away_history
            )

            target_version = None
            if hasattr(self.version_service, "get_version_for_sport"):
                target_version = self.version_service.get_version_for_sport(
                    game.sport,
                    default=None,
                )

            if target_version:
                try:
                    model = self.model_registry.get_model(
                        game.sport,
                        version=target_version,
                    )
                except PredictionException:
                    model = self.model_registry.get_model(game.sport)
            else:
                model = self.model_registry.get_model(game.sport)

            model_result = model.predict(
                home_team_name=game.home_team.name,
                away_team_name=game.away_team.name,
                home_performance=home_performance,
                away_performance=away_performance,
                home_features=home_features,
                away_features=away_features,
                analytics=getattr(game, "analytics", None),
            )

            home_score = model_result["home_score"]
            away_score = model_result["away_score"]
            recommendation = model_result["recommendation"]
            explanation = model_result["explanation"]
            raw_confidence = model_result["confidence"]

            confidence = self.confidence_service.calculate_confidence(
                home_score,
                away_score,
                home_features,
                away_features,
                getattr(game, "analytics", None),
            )

            confidence = (confidence + raw_confidence) / 2

            confidence = self.calibration_service.calibrated_confidence(
                raw_confidence=confidence,
                db=db,
            )

            model_version = model_result["metadata"]["version"]

            if confidence <= LOW_CONFIDENCE:
                confidence_level = "LOW"

            elif confidence <= MODERATE_CONFIDENCE:
                confidence_level = "MODERATE"

            elif confidence <= HIGH_CONFIDENCE:
                confidence_level = "STRONG"

            else:
                confidence_level = "ELITE"

            prediction = NikScore(

                game_id=game.id,

                home_score=home_score,

                away_score=away_score,

                confidence=confidence,

                confidence_level=confidence_level,

                model_version=model_version,

                explanation=explanation,

                recommendation=recommendation

            )

            market_evaluation = None
            if hasattr(db, "query"):
                market_evaluation = self.market_intelligence_service.evaluate_game(
                    db,
                    game,
                    prediction,
                )
                if market_evaluation is not None:
                    explanation = dict(explanation or {})
                    explanation["market_intelligence"] = market_evaluation
                    prediction.explanation = explanation

            db.add(prediction)
            db.flush()

            if market_evaluation is not None:
                self.market_intelligence_service.save_market_value(
                    db,
                    game_id=game.id,
                    evaluation=market_evaluation,
                )

            self.snapshot_service.save_snapshot(
                db=db,
                game_id=game.id,
                model_version=model_version,
                prediction=recommendation,
                confidence=confidence,
                home_score=home_score,
                away_score=away_score,
                home_features=home_features,
                away_features=away_features,
                commit=False,
            )

            self.snapshot_service.save_feature_snapshots(
                db=db,
                prediction_id=prediction.id,
                model_version=model_version,
                home_features=home_features,
                away_features=away_features,
                confidence=confidence,
                commit=False,
            )

            db.commit()
            db.refresh(prediction)

            self.monitor.log_prediction(
                "Generated prediction",
                game_id=game.id,
                sport=game.sport,
                model_name=model_result["metadata"]["model_name"],
                model_version=model_version,
                confidence=confidence,
                recommendation=recommendation,
                elapsed_ms=round((perf_counter() - started_at) * 1000, 2),
            )
            performance_metrics.record_prediction_latency(
                round((perf_counter() - started_at) * 1000, 2)
            )

            return prediction

        except Exception as error:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            self.monitor.log_exception(
                "Prediction failed",
                game_id=game_id,
                error=error,
                elapsed_ms=elapsed_ms,
            )
            raise


def create_prediction(
    db: Session,
    prediction: PredictionCreate,
):
    db_prediction = Prediction(
        **prediction.model_dump()
    )

    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)

    return db_prediction


def get_predictions(
    db: Session,
):
    return (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .all()
    )


def get_prediction_by_id(
    db: Session,
    prediction_id: int,
):
    return (
        db.query(Prediction)
        .filter(
            Prediction.id == prediction_id
        )
        .first()
    )

