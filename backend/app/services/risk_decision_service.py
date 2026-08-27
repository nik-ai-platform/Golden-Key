from __future__ import annotations


class RiskDecisionService:
    def evaluate(self, payload: dict | None) -> dict:
        payload = payload or {}
        bankroll = float(payload.get("bankroll", 5000) or 5000)
        exposure = float(payload.get("portfolio_exposure", 0.2) or 0.2)
        correlation = float(payload.get("correlation", 0.2) or 0.2)
        volatility = float(payload.get("volatility", 0.3) or 0.3)
        downside_risk = float(payload.get("downside_risk", 0.2) or 0.2)

        risk_score = round((exposure + correlation + volatility + downside_risk) / 4 * 100, 1)
        action = "Reduce position" if risk_score >= 55 else "Maintain position"
        return {
            "bankroll": bankroll,
            "risk_score": risk_score,
            "action": action,
            "reason": "Portfolio already exposed" if action == "Reduce position" else "Risk profile acceptable",
        }
