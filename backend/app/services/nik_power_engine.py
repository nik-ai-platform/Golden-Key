class NikPowerEngine:
    """
    Calculates Nik Power Index scores.
    Score range: 0-100
    """

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
        analytics
    ):

        score = 0

        # Team win strength (30%)
        win_score = (
            (performance.win_percentage or 0)
            * 100
        )

        score += win_score * 0.30

        # Offensive strength (20%)
        offense_score = self.normalize(
            performance.avg_points_for,
            15,
            35
        )

        score += offense_score * 0.20

        # Defensive strength (20%)
        defense_score = self.normalize(
            35 - performance.avg_points_against,
            0,
            20
        )

        score += defense_score * 0.20

        # Market confidence (20%)
        if analytics:
            market_score = (
                analytics.implied_home_probability
                or 0
            ) * 100

            score += market_score * 0.20

        # Home advantage (10%)
        if analytics and analytics.favorite_is_home:
            score += 10

        return round(
            min(score, 100),
            2
        )
