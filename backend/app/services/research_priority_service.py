from __future__ import annotations

from typing import Any


class ResearchPriorityService:
    def rank(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []

        for task in tasks:
            impact = float(task.get("potential_impact", 0.6) or 0.6)
            confidence = float(task.get("confidence", 0.5) or 0.5)
            availability = float(task.get("data_availability", 0.7) or 0.7)
            importance = float(task.get("model_importance", 0.6) or 0.6)
            improvement = float(task.get("expected_improvement", 0.5) or 0.5)

            score = round(
                impact * 0.30
                + confidence * 0.15
                + availability * 0.15
                + importance * 0.20
                + improvement * 0.20,
                4,
            )

            ranked.append(
                {
                    **task,
                    "priority_score": score,
                }
            )

        ranked.sort(key=lambda item: float(item["priority_score"]), reverse=True)

        for index, item in enumerate(ranked, start=1):
            item["priority_rank"] = index

        return ranked
