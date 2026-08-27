from __future__ import annotations

from typing import Any


class IntelligencePlanningService:
    def create_research_plan(self, objective: str) -> dict[str, Any]:
        steps = [
            "Analyze pace",
            "Study injuries",
            "Run simulations",
            "Update weights",
        ]
        return {
            "objective": objective,
            "plan": steps,
        }

    def evaluate_objectives(self, objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for item in objectives:
            impact = float(item.get("impact", 0.5) or 0.5)
            urgency = float(item.get("urgency", 0.5) or 0.5)
            score = round(impact * 0.65 + urgency * 0.35, 4)
            scored.append({**item, "score": score})
        scored.sort(key=lambda x: float(x["score"]), reverse=True)
        return scored

    def recommend_actions(self, evaluated: list[dict[str, Any]]) -> list[str]:
        if not evaluated:
            return ["Collect additional data"]
        top = evaluated[0]
        return [
            f"Prioritize objective: {top.get('objective', 'Unknown')}",
            "Schedule validation backtests",
            "Queue model update behind human approval",
        ]

    def prioritize_opportunities(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.evaluate_objectives(opportunities)
