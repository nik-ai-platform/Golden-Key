from app.services.historical_performance_service import (
    HistoricalPerformanceService
)
from app.services.opponent_strength_service import (
    OpponentStrengthService
)
from app.services.prediction_snapshot_service import (
    PredictionSnapshotService
)
from app.services.model_weight_service import (
    ModelWeightService
)


class NikPowerEngine:
    """
    Calculates Nik Power Index scores.
    Score range: 0-100
    """

    def __init__(
        self,
        historical_service=None,
        opponent_service=None,
        weight_service=None,
    ):

        self.historical_service = (
            historical_service or HistoricalPerformanceService()
        )

        self.opponent_service = (
            opponent_service or OpponentStrengthService()
        )

        self.weight_service = (
            weight_service or ModelWeightService()
        )

    def normalize(
        self,
        value,
        minimum,
        maximum
    ):
        if value <= minimum:
            return 0

        if value >= maximum:
            return 100

        return round(
            ((value - minimum) /
             (maximum - minimum)) * 100,
            2
        )

    def calculate_team_score(
        self,
        performance,
        analytics,
        features=None,
        is_home=True
    ):

        if not performance:
            return {
                "score": 50,
                "components": {
                    "strength": 50,
                    "form": 50,
                    "offense_defense": 50,
                    "market": 50,
                    "situational": 50
                }
            }

        strength_score = self._strength_score(
            performance
        )

        recent_form_score = self._bounded_score(
            performance.recent_form
        )

        offense_defense_score = (
            self._offense_defense_score(
                performance
            )
        )

        odds_market_score = (
            self._odds_market_score(
                analytics,
                is_home
            )
        )

        historical_score = (
            self._historical_score(
                features
            )
        )

        opponent_strength_score = (
            self._opponent_strength_score(
                features
            )
        )

        situational_score = (
            self._situational_score(
                analytics,
                is_home
            )
        )

        weights = (
            self.weight_service
            .get_weights()
        )

        score = (

            strength_score *
            weights["strength"]
            +
            recent_form_score *
            weights["recent_form"]
            +
            offense_defense_score *
            weights["offense_defense"]
            +
            historical_score *
            weights["historical"]
            +
            opponent_strength_score *
            weights["opponent_strength"]
            +
            odds_market_score *
            weights["odds_market"]
            +
            situational_score *
            weights["situational"]

        )

        return {

            "score":
                round(
                    self._bounded_score(score),
                    2
                ),

            "components": {

                "strength":
                    strength_score,

                "form":
                    recent_form_score,

                "offense_defense":
                    offense_defense_score,

                "market":
                    odds_market_score,

                "situational":
                    situational_score
            }
        }

    def _bounded_score(
        self,
        value,
        default=50
    ):

        if value is None:
            value = default

        return max(
            0,
            min(value, 100)
        )

    def _strength_score(
        self,
        performance
    ):

        games = (
            performance.wins +
            performance.losses
        )

        if games == 0:
            return 50

        return round(
            (
                performance.wins /
                games
            ) * 100,
            2
        )

    def _offense_defense_score(
        self,
        performance
    ):

        offense = self._bounded_score(
            performance.offensive_rating
        )

        defense = self._bounded_score(
            performance.defensive_rating
        )

        return round(
            (offense + defense) / 2,
            2
        )

    def _odds_market_score(
        self,
        analytics,
        is_home
    ):

        if not analytics:
            return 50

        implied_probability = (
            analytics.implied_home_probability
            if is_home
            else analytics.implied_away_probability
        )

        if implied_probability is None:
            return 50

        return self._bounded_score(
            implied_probability * 100
        )

    def _situational_score(
        self,
        analytics,
        is_home
    ):

        if not analytics:
            return 50

        rest_days = (
            analytics.home_rest_days
            if is_home
            else analytics.away_rest_days
        ) or 0

        back_to_back = (
            analytics.home_back_to_back
            if is_home
            else analytics.away_back_to_back
        )

        rest_component = self._bounded_score(
            50 + (rest_days * 10)
        )

        back_to_back_component = (
            0 if back_to_back else 100
        )

        favorite_bonus_component = 50

        if analytics.favorite_is_home is not None:
            team_is_favorite = (
                analytics.favorite_is_home
                if is_home
                else not analytics.favorite_is_home
            )

            favorite_bonus_component = (
                100 if team_is_favorite else 0
            )

        return round(
            (
                rest_component +
                back_to_back_component +
                favorite_bonus_component
            ) / 3,
            2
        )

    def _historical_score(
        self,
        features
    ):

        if not features:

            return 50


        recent_form = (
            features.get(
                "recent_form",
                50
            )
        )


        win_rate = (
            features.get(
                "win_rate",
                50
            )
        )


        trend = (
            features.get(
                "trend",
                50
            )
        )


        return round(

            (
                recent_form
                +
                win_rate
                +
                trend
            )
            /
            3,

            2
        )

    def calculate_opponent_strength(
        self,
        opponent_scores
    ):

        return (
            self.opponent_service
            .calculate_strength_adjustment(
                opponent_scores
            )
        )

    def _opponent_strength_score(
        self,
        features
    ):

        if not features:

            return 50


        return features.get(
            "opponent_strength",
            50
        )
