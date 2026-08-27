class CoachContextService:
    def build_context(self, user_id, question=None, profile=None, bets=None, predictions=None, strategy_history=None):
        profile = profile or {"risk_level": "MODERATE", "preferred_sports": ["NBA"], "bankroll": 5000}
        bets = bets or [{"id": 1, "game": "Boston vs Miami", "recommendation": "Boston -3"}]
        predictions = predictions or [{"id": 1, "game": "Boston vs Miami", "recommendation": "Boston -3"}]
        strategy_history = strategy_history or [{"name": "Conservative ATS", "result": "positive"}]

        return {
            "user_id": user_id,
            "question": question,
            "profile": profile,
            "bets": bets,
            "predictions": predictions,
            "strategy_history": strategy_history,
            "risk_summary": "Moderate risk profile with positive recent results",
        }
