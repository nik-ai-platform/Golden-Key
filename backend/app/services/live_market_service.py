class LiveMarketService:
    def compare(self, live_model, live_odds):
        live_model = live_model or {}
        live_odds = live_odds or {}
        probability = float(live_model.get("win_probability", 0) or 0)
        market = float(live_odds.get("market", 0) or 0)
        if probability >= 67 and market <= 5:
            return {"signal": "LIVE VALUE FOUND", "value": "high"}
        return {"signal": "NO EDGE", "value": "low"}
