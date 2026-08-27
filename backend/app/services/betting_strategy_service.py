from app.services.risk_service import RiskService


class BettingStrategyService:

    def __init__(self, risk_service=None):
        self.risk_service = risk_service or RiskService()

    def evaluate_bet(self, prediction, market_value, confidence):
        if prediction is None or market_value is None:
            return {
                "value_score": 0,
                "risk_score": 100,
                "quality_score": 0,
                "recommendation": "AVOID",
                "label": "❌ AVOID",
            }

        market_edge = max(0, int((prediction - market_value) * 10))
        confidence_score = max(0, min(100, int(confidence)))
        value_score = min(100, int((confidence_score * 0.6) + (market_edge * 0.4)))
        risk_score = self._derive_risk_score(confidence_score, market_edge)
        quality_score = self.calculate_quality_score(
            {
                "confidence": confidence_score,
                "market_edge": market_edge,
                "historical_edge": min(100, max(0, value_score - 10)),
                "risk_score": risk_score,
            }
        )
        action = self.recommend_action(quality_score)
        return {
            "value_score": value_score,
            "risk_score": risk_score,
            "quality_score": quality_score,
            "recommendation": action["recommendation"],
            "label": action["label"],
        }

    def calculate_risk(self, bet):
        if not isinstance(bet, dict):
            return {
                "risk_score": 0,
                "risk_level": "LOW",
            }

        return self.risk_service.calculate_risk(
            {
                "uncertainty": bet.get("uncertainty", "LOW"),
                "market_agreement": bet.get("market_agreement", "STRONG"),
                "sample_size": bet.get("sample_size", "MEDIUM"),
                "injury_uncertainty": bet.get("injury_uncertainty", False),
            }
        )

    def calculate_quality_score(self, factors):
        confidence = max(0, min(100, int(factors.get("confidence", 0))))
        market_edge = max(0, min(100, int(factors.get("market_edge", 0))))
        historical_edge = max(0, min(100, int(factors.get("historical_edge", 0))))
        risk_adjustment = max(0, min(100, int(factors.get("risk_score", 0))))

        weighted = (
            (confidence * 0.35)
            + (market_edge * 0.35)
            + (historical_edge * 0.20)
            + ((100 - risk_adjustment) * 0.10)
        )
        return int(round(weighted))

    def recommend_action(self, score):
        if score >= 90:
            return {"recommendation": "ELITE_VALUE", "label": "🔥 ELITE VALUE"}
        if score >= 75:
            return {"recommendation": "STRONG_BET", "label": "✅ STRONG BET"}
        if score >= 60:
            return {"recommendation": "LEAN", "label": "⚠ LEAN"}
        if score >= 40:
            return {"recommendation": "PASS", "label": "➖ PASS"}
        return {"recommendation": "AVOID", "label": "❌ AVOID"}

    def rank_opportunities(self, opportunities):
        return sorted(
            opportunities,
            key=lambda item: (
                item.get("quality_score", 0),
                item.get("confidence", 0),
            ),
            reverse=True,
        )

    def _derive_risk_score(self, confidence_score, market_edge):
        risk = 100 - confidence_score
        risk = max(0, min(100, risk + (max(0, 20 - market_edge) // 5)))
        return risk
