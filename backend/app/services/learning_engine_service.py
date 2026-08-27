from __future__ import annotations

from typing import Any


class LearningEngineService:
    def analyze_results(self, outcomes: list[dict[str, Any]] | None):
        outcomes = outcomes or []
        total = len(outcomes)
        failed = sum(1 for item in outcomes if item.get("actual_result") != item.get("prediction"))
        return {
            "total_outcomes": total,
            "error_rate": round((failed / total) * 100, 2) if total else 0.0,
            "signal": "needs review" if failed else "healthy",
        }

    def identify_errors(self, predictions: list[dict[str, Any]] | None):
        predictions = predictions or []
        return [
            {
                "model_name": item.get("model_name", "NPI"),
                "prediction": item.get("prediction"),
                "actual_result": item.get("actual_result"),
                "error_score": abs(float(item.get("error_score", 0.0) or 0.0)),
            }
            for item in predictions
        ]

    def generate_improvements(self, findings: dict[str, Any] | None):
        findings = findings or {}
        suggestions = []
        if findings.get("error_rate", 0) > 20:
            suggestions.append({"issue": "High error rate", "suggested_change": "Reweight recent features", "expected_impact": "+1.4% ROI", "risk_level": "Medium"})
        else:
            suggestions.append({"issue": "Stable performance", "suggested_change": "Maintain current calibration", "expected_impact": "Preserve stability", "risk_level": "Low"})
        return suggestions

    def validate_changes(self, changes: list[dict[str, Any]] | None):
        changes = changes or []
        return {
            "approved": bool(changes),
            "status": "approved" if changes else "reverted",
            "changes": changes,
        }
