class LearningFeedbackService:

    def suggest_improvement(self, weakness):
        if not weakness:
            return {"finding": "No weakness detected", "recommendation": "Maintain current approach"}

        return {
            "finding": weakness,
            "recommendation": "Reduce favorite confidence weighting",
        }

    def should_propose_change(self, weakness):
        return bool(weakness)
