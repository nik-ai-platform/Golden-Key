from abc import ABC, abstractmethod
from datetime import date

from app.core.constants import HIGH_CONFIDENCE
from app.core.constants import LOW_CONFIDENCE
from app.core.constants import MODERATE_CONFIDENCE


class BasePredictionModel(ABC):
    """Contract for all sport-specific prediction models."""

    MODEL_NAME = "BasePredictionModel"
    MODEL_VERSION = "0.0.1"
    SUPPORTED_SPORT = "unknown"
    BUILD_DATE = date(2026, 8, 5).isoformat()

    def metadata(self) -> dict[str, str]:
        return {
            "model_name": self.MODEL_NAME,
            "version": self.MODEL_VERSION,
            "supported_sport": self.SUPPORTED_SPORT,
            "build_date": self.BUILD_DATE,
        }

    def predict(
        self,
        *,
        home_team_name: str,
        away_team_name: str,
        home_performance,
        away_performance,
        home_features: dict,
        away_features: dict,
        analytics=None,
    ) -> dict:
        home_score = self.calculate_score(
            performance=home_performance,
            analytics=analytics,
            features=home_features,
            is_home=True,
        )
        away_score = self.calculate_score(
            performance=away_performance,
            analytics=analytics,
            features=away_features,
            is_home=False,
        )

        recommendation = (
            home_team_name
            if home_score >= away_score
            else away_team_name
        )

        confidence = self.calculate_confidence(
            home_score=home_score,
            away_score=away_score,
            home_features=home_features,
            away_features=away_features,
            analytics=analytics,
        )

        return {
            "home_score": round(float(home_score), 2),
            "away_score": round(float(away_score), 2),
            "recommendation": recommendation,
            "confidence": round(float(confidence), 2),
            "confidence_level": self._confidence_level(confidence),
            "explanation": self.explain_prediction(
                home_score=home_score,
                away_score=away_score,
                recommendation=recommendation,
                home_features=home_features,
                away_features=away_features,
                analytics=analytics,
            ),
            "metadata": self.metadata(),
        }

    @abstractmethod
    def calculate_score(
        self,
        *,
        performance,
        analytics,
        features: dict,
        is_home: bool,
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    def calculate_confidence(
        self,
        *,
        home_score: float,
        away_score: float,
        home_features: dict,
        away_features: dict,
        analytics,
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    def explain_prediction(
        self,
        *,
        home_score: float,
        away_score: float,
        recommendation: str,
        home_features: dict,
        away_features: dict,
        analytics,
    ) -> dict:
        raise NotImplementedError

    def _bounded(self, value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
        return max(minimum, min(maximum, float(value)))

    def _feature_value(self, features: dict, keys: tuple[str, ...], default: float = 50.0) -> float:
        payload = features or {}
        for key in keys:
            if key in payload and payload[key] is not None:
                return float(payload[key])
        return default

    def _performance_value(self, performance, field_name: str, default: float = 50.0) -> float:
        if performance is None:
            return default
        value = getattr(performance, field_name, None)
        if value is None:
            return default
        return float(value)

    def _confidence_level(self, confidence: float) -> str:
        if confidence <= LOW_CONFIDENCE:
            return "LOW"
        if confidence <= MODERATE_CONFIDENCE:
            return "MODERATE"
        if confidence <= HIGH_CONFIDENCE:
            return "STRONG"
        return "ELITE"
