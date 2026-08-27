class CorrelationService:

    def detect_correlation(self, bet_a, bet_b):
        if not bet_a or not bet_b:
            return {
                "correlation_score": 0,
                "classification": "INDEPENDENT",
            }

        same_game = bet_a.get("game_id") == bet_b.get("game_id")
        same_team = bet_a.get("team") == bet_b.get("team")
        opposing_outcomes = (
            "ML" in str(bet_a.get("selection", ""))
            and "-" in str(bet_b.get("selection", ""))
        )

        if same_game and same_team:
            return {
                "correlation_score": 90,
                "classification": "HIGHLY_CORRELATED",
            }
        if same_game and opposing_outcomes:
            return {
                "correlation_score": 75,
                "classification": "CONFLICTING",
            }
        if same_game:
            return {
                "correlation_score": 50,
                "classification": "MODERATE",
            }

        return {
            "correlation_score": 10,
            "classification": "INDEPENDENT",
        }
