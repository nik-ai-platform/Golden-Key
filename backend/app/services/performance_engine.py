class PerformanceEngine:

    def calculate_win_percentage(
        self,
        wins,
        losses
    ):

        total = wins + losses

        if total == 0:
            return 0

        return round(
            wins / total,
            4
        )

    def calculate_average(
        self,
        total,
        games
    ):

        if games == 0:
            return 0

        return round(
            total / games,
            2
        )

    def calculate_team_strength(
        self,
        performance
    ):

        offensive = (
            performance.avg_points_for
            or 0
        )

        defense = (
            performance.avg_points_against
            or 0
        )

        return round(
            offensive - defense,
            2
        )
