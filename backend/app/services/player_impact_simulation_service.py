from __future__ import annotations

from typing import Any


class PlayerImpactSimulationService:
    def simulate_impact(self, player_state: str, impact: dict[str, Any] | None = None) -> dict[str, Any]:
        state = (player_state or "Starter Available").lower()
        if "out" in state:
            return {"win_probability_change": -11.5, "spread_impact": 3.2, "replacement": "Backup Replacement"}
        if "limited" in state:
            return {"win_probability_change": -4.1, "spread_impact": 1.4, "replacement": "Starter Limited"}
        return {"win_probability_change": 0.0, "spread_impact": 0.0, "replacement": "Starter Available"}
