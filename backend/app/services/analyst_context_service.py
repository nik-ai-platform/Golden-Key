class AnalystContextService:

    def build_context(self, game_id, analytics=None):
        if not game_id:
            return {
                "game": "Unknown",
                "prediction": "No prediction",
                "confidence": 0,
                "edge": 0.0,
                "risk": "LOW",
            }

        if analytics is None:
            analytics = {}

        return {
            "game": analytics.get("game", f"Game {game_id}"),
            "prediction": analytics.get("prediction", "No prediction"),
            "confidence": int(analytics.get("confidence", 0) or 0),
            "edge": float(analytics.get("edge", 0.0) or 0.0),
            "risk": analytics.get("risk", "LOW"),
            "recent_performance": analytics.get("recent_performance", []),
            "market_edge": analytics.get("market_edge", 0.0),
            "historical_results": analytics.get("historical_results", []),
            "risk_factors": analytics.get("risk_factors", []),
        }
