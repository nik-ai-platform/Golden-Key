class ExposureService:

    def calculate_exposure(self, portfolio):
        if not portfolio:
            return {
                "daily_risk": 0,
                "sport_exposure": {},
                "team_exposure": {},
                "market_exposure": {},
                "correlation_exposure": {},
                "status": "BLOCKED",
            }

        daily_risk = float(portfolio.get("daily_risk", 0) or 0)
        limit = float(portfolio.get("daily_limit", 0) or 0)
        status = "Allowed" if daily_risk <= limit else "Blocked"

        return {
            "daily_risk": round(daily_risk, 2),
            "sport_exposure": portfolio.get("sport_exposure", {}),
            "team_exposure": portfolio.get("team_exposure", {}),
            "market_exposure": portfolio.get("market_exposure", {}),
            "correlation_exposure": portfolio.get("correlation_exposure", {}),
            "status": status,
        }

    def apply_risk_rules(self, recommended_stake, risk_score, limit):
        if risk_score > 75 and recommended_stake > limit:
            return round(limit * 0.5, 2)
        return round(recommended_stake, 2)
