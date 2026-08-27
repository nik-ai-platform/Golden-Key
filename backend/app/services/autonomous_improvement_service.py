from __future__ import annotations

from typing import Any


class AutonomousImprovementService:
    def propose(self, model_name: str, issue: dict[str, Any]) -> dict[str, Any]:
        problem = str(issue.get("problem", "Rest weighting low"))
        change = str(issue.get("suggested_change", "Increase rest weight +3"))
        expected = float(issue.get("expected_impact_pct", 1.2) or 1.2)
        risk = str(issue.get("risk", "medium"))

        return {
            "current_model": model_name,
            "problem": problem,
            "suggested_change": change,
            "expected_impact": f"+{expected:.1f}% ATS",
            "risk": risk,
            "required_validation": [
                "Backtest last 5 seasons",
                "Cross-validate by conference and schedule density",
                "Run out-of-sample simulation",
            ],
        }
