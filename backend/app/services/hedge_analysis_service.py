from __future__ import annotations


class HedgeAnalysisService:
    def analyze(self, position: dict | None) -> dict:
        position = position or {}
        market = str(position.get("market", "")).lower()
        if "lakers" in market:
            return {"risk": "High", "potential_hedge": "Warriors +6", "expected_value": 0.8}
        return {"risk": "Moderate", "potential_hedge": "Opposing position", "expected_value": 0.3}
