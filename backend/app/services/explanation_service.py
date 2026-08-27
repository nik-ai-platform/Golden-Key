class ExplanationService:


    def generate_explanation(
        self,
        home_components,
        away_components,
        recommendation
    ):

        reasons = []


        if (
            home_components["strength"]
            >
            away_components["strength"]
        ):
            reasons.append(
                "Home team has superior season strength"
            )

        else:
            reasons.append(
                "Away team has superior season strength"
            )


        if (
            home_components["form"]
            >
            away_components["form"]
        ):
            reasons.append(
                "Home team has stronger recent form"
            )

        else:
            reasons.append(
                "Away team has stronger recent form"
            )


        if (
            home_components["offense_defense"]
            >
            away_components["offense_defense"]
        ):
            reasons.append(
                "Home team has better offensive/defensive profile"
            )

        else:
            reasons.append(
                "Away team has better offensive/defensive profile"
            )


        return {
            "recommendation": recommendation,
            "reasons": reasons
        }
