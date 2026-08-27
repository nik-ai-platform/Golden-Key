from __future__ import annotations

from typing import Any


class ContextAwarenessService:
    def assess(self, context: dict[str, Any]) -> dict[str, Any]:
        season_stage = str(context.get("season_stage", "regular")).lower()
        playoff_pressure = "high" if season_stage == "playoffs" else "low"

        return {
            "season_stage": season_stage,
            "playoff_pressure": playoff_pressure,
            "travel": context.get("travel", "normal"),
            "weather": context.get("weather", "neutral"),
            "motivation": context.get("motivation", "standard"),
            "schedule": context.get("schedule", "balanced"),
            "intensity": "higher" if season_stage == "playoffs" else "lower",
        }
