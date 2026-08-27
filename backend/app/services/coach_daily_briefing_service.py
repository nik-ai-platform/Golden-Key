class CoachDailyBriefingService:
    def build_briefing(self, profile=None):
        profile = profile or {"risk_level": "MODERATE", "preferred_sports": ["NBA"], "bankroll": 5000}

        return {
            "headline": "Good Morning",
            "profile": profile,
            "focus": [
                "NBA ATS opportunities",
                "Avoid high variance parlays",
                "Best value window: afternoon games",
            ],
        }
