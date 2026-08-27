from __future__ import annotations


class FeatureDriftService:
    """Monitors feature distribution shifts and flags drift."""

    def detect_drift(self, feature_name: str, historical_mean: float, current_mean: float) -> dict[str, str | float]:
        delta = abs(float(current_mean) - float(historical_mean))
        status = "Drift Detected" if delta >= 1.5 else "Stable"
        return {
            "feature": feature_name,
            "historical_mean": float(historical_mean),
            "current_mean": float(current_mean),
            "status": status,
        }
