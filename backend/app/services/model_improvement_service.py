from __future__ import annotations


class ModelImprovementService:
    def recommend(self, issue: str | None = None) -> dict:
        issue = issue or "Road teams undervalued"
        return {
            "issue": issue,
            "suggested_change": "Increase travel penalty",
            "expected_impact": "+1.4% ROI",
            "risk_level": "Low",
        }
