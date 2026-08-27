from app.core.constants import MAX_SCORE
from app.core.constants import MIN_SCORE


class ValidationService:
    """
    Validates incoming prediction data.
    """


    def validate_game(
        self,
        game
    ):

        if not game:

            return False


        if not game.home_team_id:

            return False


        if not game.away_team_id:

            return False


        return True



    def validate_score(
        self,
        score
    ):

        if score is None:

            return False


        return (
            MIN_SCORE <= score <= MAX_SCORE
        )
