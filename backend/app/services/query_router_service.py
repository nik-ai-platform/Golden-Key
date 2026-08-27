from __future__ import annotations


class QueryRouterService:
    def route(self, message: str) -> str:
        text = (message or "").lower()

        if any(keyword in text for keyword in ["pick", "prediction", "best nba", "tonight", "bet"]):
            return "Prediction Service"
        if any(keyword in text for keyword in ["risk", "portfolio", "bankroll", "too much"]):
            return "Portfolio Risk Service"
        if any(keyword in text for keyword in ["live", "score", "injury", "odds"]):
            return "Live Intelligence"
        return "General Question"
