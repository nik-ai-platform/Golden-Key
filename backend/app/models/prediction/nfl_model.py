from app.models.prediction.base_model import BasePredictionModel


class NFLPredictionModel(BasePredictionModel):
    MODEL_NAME = "NFL Prediction Model"
    MODEL_VERSION = "NFL-v1"
    SUPPORTED_SPORT = "americanfootball_nfl"

    def calculate_score(
        self,
        *,
        performance,
        analytics,
        features: dict,
        is_home: bool,
    ) -> float:
        # NFL weighting: turnover margin, QB play, pressure, red-zone, rest/travel.
        turnover_differential = self._feature_value(features, ("turnover_differential", "trend"), default=50.0)
        quarterback_performance = self._feature_value(features, ("quarterback_performance", "offense", "scoring_average"))
        pressure_rate = self._feature_value(features, ("pressure_rate", "defense", "defense_average"))
        red_zone_efficiency = self._feature_value(features, ("red_zone_efficiency", "strength", "win_rate"))
        rest_days = self._feature_value(features, ("rest_days",), default=1.0)

        travel_adjustment = -4.0 if (not is_home and rest_days <= 0) else 0.0
        home_field = 4.0 if is_home else 0.0

        raw_score = (
            turnover_differential * 0.24
            + quarterback_performance * 0.24
            + pressure_rate * 0.18
            + red_zone_efficiency * 0.22
            + (50.0 + rest_days * 7.0) * 0.12
            + travel_adjustment
            + home_field
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
        turnover_gap = abs(
            self._feature_value(home_features, ("turnover_differential", "trend"))
            - self._feature_value(away_features, ("turnover_differential", "trend"))
        )
        base = 56.0 + (spread * 0.35)
        return round(self._bounded(base + (turnover_gap * 0.07)), 2)

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
            "Turnover differential and quarterback performance drove NFL weighting.",
            "Pressure rate and red-zone efficiency influenced expected game control.",
            "Rest/travel and home-field factors were applied to final score.",
        ]
        return {
            "recommendation": recommendation,
            "score_gap": round(abs(home_score - away_score), 2),
            "reasons": reasons,
        }
