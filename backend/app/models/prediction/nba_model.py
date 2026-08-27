from app.models.prediction.base_model import BasePredictionModel


class NBAPredictionModel(BasePredictionModel):
    MODEL_NAME = "NBA Prediction Model"
    MODEL_VERSION = "NBA-v1"
    SUPPORTED_SPORT = "basketball_nba"

    def calculate_score(
        self,
        *,
        performance,
        analytics,
        features: dict,
        is_home: bool,
    ) -> float:
        # NBA weighting: pace, efficiency, rest, home court, and recent form.
        pace = self._feature_value(features, ("pace", "offense", "scoring_average"))
        offensive_efficiency = self._performance_value(performance, "offensive_rating", default=pace)
        defensive_efficiency = self._performance_value(performance, "defensive_rating", default=50.0)
        rest_days = self._feature_value(features, ("rest_days",), default=1.0)
        recent_form = self._feature_value(features, ("recent_form", "form", "win_rate"))

        home_court = 7.0 if is_home else -2.0
        rest_component = 50.0 + ((rest_days - 1.0) * 8.0)

        raw_score = (
            offensive_efficiency * 0.30
            + pace * 0.20
            + (100.0 - defensive_efficiency) * 0.15
            + recent_form * 0.20
            + rest_component * 0.15
            + home_court
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
        pace_gap = abs(
            self._feature_value(home_features, ("pace", "offense"))
            - self._feature_value(away_features, ("pace", "offense"))
        )
        base = 55.0 + (spread * 0.30)
        return round(self._bounded(base + (pace_gap * 0.08)), 2)

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
            "Pace and offensive efficiency were emphasized for NBA scoring.",
            "Recent form and rest days were included in the weighted score.",
            "Home-court context adjusted the final matchup edge.",
        ]
        return {
            "recommendation": recommendation,
            "score_gap": round(abs(home_score - away_score), 2),
            "reasons": reasons,
        }
