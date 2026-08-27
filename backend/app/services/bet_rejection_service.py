class BetRejectionService:
    def explain_rejection(self, bet=None, context=None):
        context = context or {}
        reasons = []

        if bet and bet.get("market_adjusted"):
            reasons.append("Market already adjusted")
        if bet and bet.get("historical_success") == "low":
            reasons.append("Low historical success")
        if context.get("risk_level") in {"CONSERVATIVE", "MODERATE"}:
            reasons.append("High volatility")

        if not reasons:
            reasons = ["Limited edge relative to your profile"]

        return {
            "bet": bet,
            "reasons": reasons,
            "summary": "This bet was downgraded because: " + "; ".join(reasons),
        }
