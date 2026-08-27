from app.core.constants import DEFAULT_SCORE
from app.core.constants import MAX_SCORE
from app.core.constants import MODERATE_SCORE


class ConfidenceService:


    def calculate_confidence(
        self,
        home_score,
        away_score,
        home_features,
        away_features,
        analytics=None
    ):

        score_difference = abs(
            home_score -
            away_score
        )


        separation_score = min(
            score_difference * 5,
            MAX_SCORE
        )


        feature_quality = (
            self._feature_quality(home_features)
            +
            self._feature_quality(away_features)
        ) / 2


        market_alignment = (
            self._market_alignment(
                analytics
            )
        )


        confidence = (

            (separation_score * 0.40)
            +
            (market_alignment * 0.30)
            +
            (feature_quality * 0.30)

        )


        return round(
            confidence,
            2
        )


    def _feature_quality(
        self,
        features
    ):

        if not features:
            return DEFAULT_SCORE


        populated = sum(
            1
            for value in features.values()
            if value is not None
        )


        return (
            populated /
            len(features)
        ) * MAX_SCORE


    def _market_alignment(
        self,
        analytics
    ):

        if not analytics:
            return DEFAULT_SCORE

        return MODERATE_SCORE
