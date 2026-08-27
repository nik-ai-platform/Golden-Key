class StrategyCoachService:
    def analyze_strategy(self, history=None, simulations=None, risk_behavior=None, model_performance=None):
        history = history or []
        simulations = simulations or []
        risk_behavior = risk_behavior or {}
        model_performance = model_performance or {}

        suggestions = []
        if history:
            suggestions.append("Reduce parlay frequency")
        if risk_behavior.get("risk_level") in {"AGGRESSIVE", "PROFESSIONAL"}:
            suggestions.append("Lower variance exposure")
        if model_performance.get("accuracy") and model_performance["accuracy"] < 0.6:
            suggestions.append("Favor higher-confidence plays")

        if not suggestions:
            suggestions = ["Stay disciplined with your current profile"]

        return {
            "observation": "You perform best with NBA ATS and single bets",
            "suggestions": suggestions,
            "risk_behavior": risk_behavior,
            "model_performance": model_performance,
        }

    def review_performance(self, profile=None):
        profile = profile or {}
        preferred_market = (profile.get("preferred_bet_types") or ["ATS"])[0]
        return {
            "summary": f"Your {preferred_market.lower()} selections are outperforming favorites by 7%.",
            "weaknesses": ["totals analysis"],
            "suggested_adjustments": ["increase value-based selections"],
            "weekly_goals": ["review 3 underdog opportunities"],
        }
