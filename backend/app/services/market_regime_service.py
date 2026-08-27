from __future__ import annotations


class MarketRegimeService:
    def detect(self, market_data: dict | None) -> dict:
        market_data = market_data or {}
        scoring = float(market_data.get("scoring", 0) or 0)
        if scoring >= 230:
            regime = "High Scoring Era"
        elif scoring <= 205:
            regime = "Low Scoring Era"
        elif market_data.get("public_bias"):
            regime = "Public Betting Bias"
        elif market_data.get("line_inflation"):
            regime = "Line Inflation"
        else:
            regime = "Favorite/Dog Cycles"
        return {"regime": regime, "message": "NBA scoring environment changed. Totals models require recalibration."}
