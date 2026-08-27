class OpponentStrengthService:

    """
    Calculates strength of schedule.
    """


    def calculate_strength_adjustment(
        self,
        opponent_scores
    ):

        if not opponent_scores:

            return 50


        average = (
            sum(opponent_scores)
            /
            len(opponent_scores)
        )


        return round(
            max(
                0,
                min(
                    100,
                    average
                )
            ),
            2
        )
