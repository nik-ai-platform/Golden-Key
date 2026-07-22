from typing import Optional


class FeatureEngine:

    """
    Calculates analytical features used by Nik AI models.
    """

    def american_to_probability(
        self,
        odds: Optional[int]
    ) -> float | None:

        if odds is None:
            return None

        if odds < 0:
            probability = (
                abs(odds) /
                (abs(odds) + 100)
            )

        else:
            probability = (
                100 /
                (odds + 100)
            )

        return round(
            probability,
            4
        )

    def calculate_moneyline_features(
        self,
        home_moneyline: int,
        away_moneyline: int
    ):

        home_probability = (
            self.american_to_probability(
                home_moneyline
            )
        )

        away_probability = (
            self.american_to_probability(
                away_moneyline
            )
        )

        favorite_is_home = (
            home_moneyline < away_moneyline
        )

        return {
            "implied_home_probability":
                home_probability,

            "implied_away_probability":
                away_probability,

            "favorite_is_home":
                favorite_is_home
        }

    def calculate_line_movement(
        self,
        opening_line: float,
        current_line: float
    ):

        if opening_line is None or current_line is None:
            return None

        return round(
            current_line - opening_line,
            2
        )