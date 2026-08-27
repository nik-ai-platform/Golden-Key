from __future__ import annotations


class PerformanceAttributionService:
    def explain(self, portfolio: dict | None) -> dict:
        portfolio = portfolio or {}
        return {
            "profit_source": portfolio.get("profit_source", "NBA Underdogs"),
            "contribution": portfolio.get("contribution", "+72% of ROI"),
            "sport": portfolio.get("sport", "NBA"),
            "market": portfolio.get("market", "ATS"),
            "strategy": portfolio.get("strategy", "Underdog value"),
            "team": portfolio.get("team", "Boston Celtics"),
            "confidence": portfolio.get("confidence", 84),
            "risk_level": portfolio.get("risk_level", "Moderate"),
        }
