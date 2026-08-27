class CommunityIntelligenceService:
    def analyze(self, payload: dict) -> dict:
        popular_picks = payload.get("popular_picks", [])
        consensus = float(payload.get("consensus", 0.0))
        market_sentiment = payload.get("market_sentiment", "neutral")
        emerging_trends = payload.get("emerging_trends", [])

        if consensus >= 0.75:
            consensus_signal = "high"
        elif consensus >= 0.6:
            consensus_signal = "medium"
        else:
            consensus_signal = "low"

        return {
            "popular_picks": popular_picks,
            "consensus": consensus,
            "consensus_signal": consensus_signal,
            "market_sentiment": market_sentiment,
            "emerging_trends": emerging_trends,
            "summary": "Consensus is building around the leading view",
        }
