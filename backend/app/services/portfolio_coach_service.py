from __future__ import annotations


class PortfolioCoachService:
    def review(self, portfolio: dict | None) -> dict:
        portfolio = portfolio or {}
        return {
            "strength": portfolio.get("strength", "NBA ATS"),
            "weakness": portfolio.get("weakness", "Overexposure to favorites"),
            "recommendation": "Increase diversification",
            "goals": ["Lower correlation", "Reduce favorite concentration", "Improve risk controls"],
        }
