from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_SCORE
from app.core.constants import LOW_TREND_SCORE
from app.core.constants import MAX_SCORE
from app.core.constants import MODERATE_SCORE
from app.repositories import game_repository


class HistoricalPerformanceService:

    """
    Calculates historical team performance.
    """

    def get_recent_games(
        self,
        db: Session,
        team_id: int,
        limit: int = 5
    ):
        return game_repository.get_recent_games_for_team(
            db,
            team_id,
            limit
        )

    def calculate_recent_form(
        self,
        games,
        team_id
    ):

        if not games:

            return DEFAULT_SCORE


        wins = 0

        total = 0


        for game in games:

            # Placeholder until final scores are connected

            total += 1


        if total == 0:

            return DEFAULT_SCORE

        return round(
            (wins / total) * MAX_SCORE,
            2
        )

    def calculate_win_rate(
        self,
        wins,
        total_games
    ):

        if total_games == 0:
            return DEFAULT_SCORE

        return round(
            (wins / total_games) * MAX_SCORE,
            2
        )

    def calculate_average(
        self,
        values
    ):

        if not values:
            return 0

        return round(
            sum(values) / len(values),
            2
        )

    def calculate_trend(
        self,
        recent_values
    ):

        if len(recent_values) < 2:
            return DEFAULT_SCORE


        first = recent_values[-1]

        last = recent_values[0]


        if last > first:
            return MODERATE_SCORE

        if last < first:
            return LOW_TREND_SCORE

        return DEFAULT_SCORE

    def build_team_profile(
        self,
        games,
        team_id
    ):

        results = []


        for game in games:

            result = (
                self.calculate_game_result(
                    game,
                    team_id
                )
            )

            if result:
                results.append(result)


        if not results:

            return {

                "games_count": 0,

                "recent_form": DEFAULT_SCORE,

                "win_rate": DEFAULT_SCORE,

                "scoring_average": 0,

                "defense_average": 0,

                "trend": DEFAULT_SCORE
            }


        wins = sum(
            1
            for result in results
            if result["won"]
        )


        points_for = [
            result["points_for"]
            for result in results
        ]


        points_against = [
            result["points_against"]
            for result in results
        ]


        return {

            "games_count":
                len(results),

            "recent_form":
                self.calculate_win_rate(
                    wins,
                    len(results)
                ),

            "win_rate":
                self.calculate_win_rate(
                    wins,
                    len(results)
                ),

            "scoring_average":
                self.calculate_average(
                    points_for
                ),

            "defense_average":
                self.calculate_average(
                    points_against
                ),

            "trend":
                self.calculate_trend(
                    points_for
                )
        }

    def calculate_game_result(
        self,
        game,
        team_id
    ):

        if (
            game.home_score is None
            or game.away_score is None
        ):
            return None


        is_home = (
            game.home_team_id ==
            team_id
        )


        team_score = (
            game.home_score
            if is_home
            else game.away_score
        )


        opponent_score = (
            game.away_score
            if is_home
            else game.home_score
        )


        won = (
            team_score >
            opponent_score
        )


        return {

            "won": won,

            "points_for":
                team_score,

            "points_against":
                opponent_score
        }
