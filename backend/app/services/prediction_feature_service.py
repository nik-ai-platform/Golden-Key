from app.services.historical_performance_service import (
    HistoricalPerformanceService
)


class PredictionFeatureService:

    """
    Converts raw team performance data
    into prediction-ready features.
    """

    def __init__(
        self,
        historical_service=None,
    ):

        self.historical_service = (
            historical_service or HistoricalPerformanceService()
        )

    def calculate_historical_features(
        self,
        db,
        team_id
    ):

        games = (
            self.historical_service.get_recent_games(
                db,
                team_id,
                10
            )
        )

        return (
            self.historical_service.build_team_profile(
                games,
                team_id
            )
        )


    def calculate_historical_features_from_games(
        self,
        games,
        team_id,
    ):
        return self.historical_service.build_team_profile(
            games,
            team_id,
        )


    def calculate_team_features(
        self,
        performance
    ):

        if not performance:
            return {
                "strength": 50,
                "offense": 50,
                "defense": 50,
                "form": 50
            }


        return {

            "strength":
                self._strength_score(
                    performance
                ),

            "offense":
                performance.offensive_rating or 50,

            "defense":
                performance.defensive_rating or 50,

            "form":
                performance.recent_form or 50
        }


    def _strength_score(
        self,
        performance
    ):

        total_games = (
            performance.wins +
            performance.losses
        )


        if total_games == 0:

            return 50

        return round(
            (
                performance.wins /
                total_games
            ) * 100,
            2
        )
