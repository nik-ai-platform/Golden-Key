from app.models.prediction.base_model import BasePredictionModel


class WNBAPredictionModel(BasePredictionModel):
    MODEL_NAME = "WNBA Prediction Model"
    MODEL_VERSION = "WNBA-v1"
    SUPPORTED_SPORT = "basketball_wnba"

    def calculate_score(
        self,
        *,
        performance,
        analytics,
        features: dict,
        is_home: bool,
    ) -> float:
        # WNBA weighting: rotation stability, travel impact, efficiency, consistency, momentum.
        offensive_efficiency = self._performance_value(performance, "offensive_rating")
        defensive_consistency = 100.0 - self._performance_value(performance, "defensive_rating")
        momentum = self._feature_value(features, ("recent_momentum", "recent_form", "form", "win_rate"))
        rotation_stability = self._feature_value(features, ("rotation_stability", "consistency"), default=55.0)
        rest_days = self._feature_value(features, ("rest_days",), default=1.0)
        travel_penalty = 6.0 if rest_days <= 0 else 0.0

        home_context = 5.0 if is_home else -1.5

        raw_score = (
            offensive_efficiency * 0.28
            + defensive_consistency * 0.20
            + momentum * 0.22
            + rotation_stability * 0.20
            + (50.0 + (rest_days * 6.0) - travel_penalty) * 0.10
            + home_context
        )
        return round(self._bounded(raw_score), 2)

    def calculate_confidence(
        self,
        *,
        home_score: float,
        away_score: float,
        home_features: dict,
        away_features: dict,
        analytics,
    ) -> float:
        spread = abs(home_score - away_score)
        momentum_gap = abs(
            self._feature_value(home_features, ("recent_momentum", "recent_form", "form"))
            - self._feature_value(away_features, ("recent_momentum", "recent_form", "form"))
        )
        base = 54.0 + (spread * 0.28)
        return round(self._bounded(base + (momentum_gap * 0.10)), 2)

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
        reasons = [
            "Rotation stability and travel impact were prioritized for WNBA context.",
            "Offensive efficiency and defensive consistency shaped baseline score.",
            "Recent momentum shifted close-match confidence outcomes.",
        ]
        return {
            "recommendation": recommendation,
            "score_gap": round(abs(home_score - away_score), 2),
            "reasons": reasons,
        }
