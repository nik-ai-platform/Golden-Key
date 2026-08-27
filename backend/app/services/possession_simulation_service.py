from __future__ import annotations

from typing import Any


class PossessionSimulationService:
    def simulate_drive(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "touchdown": 28,
            "field_goal": 21,
            "punt": 42,
            "turnover": 9,
            "context": context or {},
        }
