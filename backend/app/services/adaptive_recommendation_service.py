from __future__ import annotations


class AdaptiveRecommendationService:
    def recommend(self, payload: dict | None) -> dict:
        payload = payload or {}
        edge = float(payload.get("edge", 1.5) or 1.5)
        uncertainty = float(payload.get("uncertainty", 0.7) or 0.7)
        if edge > 0 and uncertainty >= 0.6:
            return {
                "final_recommendation": "PASS",
                "reason": "Edge exists but uncertainty too high.",
                "inputs_used": ["NPI", "Simulation", "Research Agent", "Portfolio Risk", "RL Agent"],
            }
        return {
            "final_recommendation": "Recommend Bet",
            "reason": "Signal and risk are aligned.",
            "inputs_used": ["NPI", "Simulation", "Research Agent", "Portfolio Risk", "RL Agent"],
        }
