from __future__ import annotations

from typing import Any


class AIStrategyGeneratorService:
    def build_strategy(self, hypothesis: dict[str, Any]) -> dict[str, Any]:
        return {
            "sport": hypothesis.get("sport", "General"),
            "if": [
                "Away team",
                "Rest disadvantage > 2 days",
                "Spread < -5",
            ],
            "then": "Evaluate ATS performance",
            "backtest": "Historical replay across multiple seasons",
            "components": [
                "Spread",
                "Location",
                "Rest",
                "Travel",
                "Weather",
                "Injuries",
                "Team Metrics",
                "Player Metrics",
                "Market Movement",
                "NPI Factors",
            ],
        }
