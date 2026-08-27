from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class ResearchPlannerService:
    def identify_questions(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        sport = str(data.get("sport", "NBA"))
        decline = float(data.get("accuracy_decline_pct", 0) or 0)
        opportunities: list[dict[str, Any]] = []

        if decline >= 3:
            opportunities.append(
                {
                    "objective": f"Why are {sport} favorites underperforming?",
                    "sport": sport,
                    "priority": "high",
                    "reason": f"{sport} model accuracy declined {decline:.1f}%",
                }
            )

        if bool(data.get("market_shift_detected", False)):
            opportunities.append(
                {
                    "objective": f"Detect recent {sport} market pricing shifts",
                    "sport": sport,
                    "priority": "medium",
                    "reason": "Odds behavior changed relative to baseline",
                }
            )

        if not opportunities:
            opportunities.append(
                {
                    "objective": f"Find {sport} total betting inefficiencies",
                    "sport": sport,
                    "priority": "medium",
                    "reason": "Continuous discovery cycle",
                }
            )

        return opportunities

    def prioritize_tasks(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority_rank = {"high": 3, "medium": 2, "low": 1}

        def _score(item: dict[str, Any]) -> int:
            return priority_rank.get(str(item.get("priority", "low")).lower(), 1)

        return sorted(opportunities, key=_score, reverse=True)

    def schedule_research(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        base_time = datetime.now(UTC)
        scheduled: list[dict[str, Any]] = []

        for index, task in enumerate(tasks):
            slot = base_time + timedelta(minutes=index * 15)
            scheduled.append(
                {
                    **task,
                    "status": "scheduled",
                    "scheduled_for": slot.isoformat() + "Z",
                }
            )

        return scheduled
