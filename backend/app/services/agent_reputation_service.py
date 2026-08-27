from __future__ import annotations


class AgentReputationService:
    def score(self, metrics: dict | None = None) -> dict:
        metrics = metrics or {}
        accuracy = float(metrics.get("accuracy", 59.2) or 59.2)
        calibration = float(metrics.get("calibration", 0.82) or 0.82)
        long_term_value = float(metrics.get("long_term_value", 0.78) or 0.78)
        quality = round((accuracy / 100 * 0.5 + calibration * 0.25 + long_term_value * 0.25) * 100, 1)
        weight = "HIGH" if quality >= 58 else "MEDIUM"
        return {
            "accuracy": accuracy,
            "prediction_quality": quality,
            "calibration": calibration,
            "long_term_value": long_term_value,
            "weight": weight,
        }
