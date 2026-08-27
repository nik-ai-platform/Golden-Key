class MarketSentimentService:
    def analyze(self, tickets_public, money_public, line_movement):
        if tickets_public is None or money_public is None:
            return {"signal": "Neutral", "reason": "Insufficient data"}

        if tickets_public > 70 and money_public < 50 and line_movement < 0:
            return {"signal": "Possible Sharp Action", "reason": "Public tickets are heavy while line moves against the public side"}
        return {"signal": "Balanced", "reason": "No clear edge"}
