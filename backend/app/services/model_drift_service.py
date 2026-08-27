from __future__ import annotations


class ModelDriftService:
    """Flags production drift based on recent model performance changes."""

    def detect_drift(self, recent_roi: float, historical_roi: float, recent_accuracy: float, historical_accuracy: float) -> dict[str, str | float]:
        roi_drop = float(historical_roi) - float(recent_roi)
        accuracy_drop = float(historical_accuracy) - float(recent_accuracy)
        status = "Possible Drift" if roi_drop > 5 or accuracy_drop > 5 else "Stable"
        return {
            "recent_roi": float(recent_roi),
            "historical_roi": float(historical_roi),
            "recent_accuracy": float(recent_accuracy),
            "historical_accuracy": float(historical_accuracy),
            "status": status,
        }
