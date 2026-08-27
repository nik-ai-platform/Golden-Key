from __future__ import annotations

from typing import Any


class ExperimentEvaluatorService:
    def evaluate(self, results: dict[str, Any]) -> dict[str, Any]:
        sample_size = int(results.get("sample_size", 0))
        ats = float(results.get("ats_percentage", 0))
        stability = "low" if sample_size < 60 else "medium" if sample_size < 300 else "high"
        overfitting_risk = "high" if sample_size < 60 else "medium" if sample_size < 300 else "low"
        return {
            "sample_size": sample_size,
            "roi": results.get("roi", 0),
            "ats_percentage": ats,
            "stability": stability,
            "variance": results.get("variance", 0.0),
            "confidence": results.get("confidence", "medium"),
            "overfitting_risk": overfitting_risk,
        }
