from __future__ import annotations


class ConfidenceAdjustmentService:
    def adjust(self, payload: dict | None) -> dict:
        payload = payload or {}
        confidence = float(payload.get("confidence", 85) or 85)
        volatility = float(payload.get("volatility", 0.0) or 0.0)
        model_health = str(payload.get("model_health", "healthy")).lower()
        sample_size = int(payload.get("sample_size", 300) or 300)

        penalty = 0.0
        if volatility >= 0.7:
            penalty += 10
        if model_health != "healthy":
            penalty += 8
        if sample_size < 100:
            penalty += 5

        adjusted = max(5.0, round(confidence - penalty, 1))
        return {
            "before": confidence,
            "adjusted": adjusted,
            "reason": "High volatility environment" if penalty >= 10 else "Stable environment",
        }
