class PreferenceLearningService:

    def learn(self, history):
        if not history:
            return {
                "preferred_strategy": "Moderate Risk",
                "preferred_sports": ["NFL"],
                "preferred_bet_types": ["ATS"],
            }

        strategy = "Moderate Risk"
        preferred_sports = []
        preferred_bet_types = []

        for item in history:
            if item.get("sport") == "NBA":
                preferred_sports.append("NBA")
            if item.get("bet_type") == "ATS":
                preferred_bet_types.append("ATS")
            if item.get("parlay"):
                strategy = "Lower Risk"
            if item.get("risk") == "low":
                strategy = "Low Risk"

        return {
            "preferred_strategy": strategy,
            "preferred_sports": sorted(set(preferred_sports or ["NBA"])),
            "preferred_bet_types": sorted(set(preferred_bet_types or ["ATS"])),
        }
