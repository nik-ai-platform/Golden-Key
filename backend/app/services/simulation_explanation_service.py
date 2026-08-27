from __future__ import annotations


class SimulationExplanationService:
    def explain(self, result: dict) -> dict:
        win_probability = float(result.get("win_probability", 0.0))
        return {
            "explanation": [
                "Defensive matchup",
                "Rest advantage",
                "Offensive efficiency",
            ],
            "risk": "Turnover variance",
            "win_probability": win_probability,
        }
