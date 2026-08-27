from __future__ import annotations

from typing import Any


class KnowledgeGapService:
    def detect_gaps(self, data: dict[str, Any]) -> dict[str, Any]:
        sport = str(data.get("sport", "NBA"))
        decline = float(data.get("accuracy_decline_pct", 0) or 0)
        unexplained = int(data.get("unexplained_outcomes", 0) or 0)
        blind_spots = list(data.get("blind_spots", []) or [])
        market_change = bool(data.get("market_shift_detected", False))

        findings: list[dict[str, str]] = []

        if decline >= 2:
            findings.append(
                {
                    "category": "Performance Declines",
                    "finding": f"{sport} model performance down {decline:.1f}%",
                    "research_needed": f"Recalibrate {sport} weighting and baseline assumptions",
                }
            )

        if unexplained > 5:
            findings.append(
                {
                    "category": "Unexplained Outcomes",
                    "finding": f"{unexplained} outcomes with weak explanatory coverage",
                    "research_needed": "Audit hidden variables and residual error clusters",
                }
            )

        findings.append(
            {
                "category": "Model Weaknesses",
                "finding": "Home advantage model outdated",
                "research_needed": "New venue impact analysis",
            }
        )

        if market_change:
            findings.append(
                {
                    "category": "Market Changes",
                    "finding": "Line movement regime appears different from baseline",
                    "research_needed": "Re-estimate closing-line efficiency by sport and market segment",
                }
            )

        if blind_spots:
            findings.append(
                {
                    "category": "Data Blind Spots",
                    "finding": f"Missing dimensions: {', '.join(str(item) for item in blind_spots)}",
                    "research_needed": "Expand feature coverage for identified blind spots",
                }
            )

        return {
            "sport": sport,
            "findings": findings,
        }
