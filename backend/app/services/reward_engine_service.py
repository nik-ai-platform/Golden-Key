from __future__ import annotations


class RewardEngineService:
    def calculate_reward(self, payload: dict | None) -> dict:
        payload = payload or {}
        correct_prediction = bool(payload.get("correct_prediction", False))
        roi_improvement = float(payload.get("roi_improvement", 0.0) or 0.0)
        risk_reduction = float(payload.get("risk_reduction", 0.0) or 0.0)
        confidence_accuracy = float(payload.get("confidence_accuracy", 0.0) or 0.0)
        long_term_stability = float(payload.get("long_term_stability", 0.0) or 0.0)

        reward = (
            (0.4 if correct_prediction else -0.4)
            + (roi_improvement * 0.2)
            + (risk_reduction * 0.15)
            + (confidence_accuracy * 0.15)
            + (long_term_stability * 0.1)
        )
        return {
            "reward": round(reward, 2),
            "components": {
                "correct_prediction": correct_prediction,
                "roi_improvement": roi_improvement,
                "risk_reduction": risk_reduction,
                "confidence_accuracy": confidence_accuracy,
                "long_term_stability": long_term_stability,
            },
        }
