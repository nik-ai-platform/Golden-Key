from __future__ import annotations

from typing import Any


class GameScenarioService:
    def simulate(self, scenario: dict[str, Any]) -> dict[str, Any]:
        description = str(scenario.get("question", ""))
        if "rain" in description.lower():
            return {"passing_efficiency": -8, "under_probability": 12, "scenario": scenario}
        if "qb" in description.lower() or "quarterback" in description.lower():
            return {"win_probability": -9.8, "spread_impact": 3.1, "scenario": scenario}
        return {"win_probability": -2.0, "spread_impact": 0.5, "scenario": scenario}
