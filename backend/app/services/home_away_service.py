from app.core.constants import DEFAULT_SCORE
from app.core.constants import MAX_SCORE
from app.core.constants import MIN_SCORE


class HomeAwayService:

    """
    Calculates home and away performance splits.
    """


    def calculate_home_advantage(
        self,
        home_wins,
        home_games,
        away_wins,
        away_games
    ):

        if home_games == 0 or away_games == 0:
            return DEFAULT_SCORE


        home_rate = (
            home_wins /
            home_games
        ) * MAX_SCORE


        away_rate = (
            away_wins /
            away_games
        ) * MAX_SCORE


        advantage = (
            home_rate -
            away_rate
        )


        return round(
            max(
                MIN_SCORE,
                min(
                    MAX_SCORE,
                    DEFAULT_SCORE + advantage
                )
            ),
            2
        )
