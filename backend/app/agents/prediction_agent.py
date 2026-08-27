from __future__ import annotations


class PredictionAgent:
    name = "prediction_agent"

    def analyze(self, game: dict) -> dict:
        return {
            "pick": "Celtics -4",
            "confidence": 78,
            "inputs": ["NPI", "Team Metrics", "Matchup Data", "Historical Performance"],
            "game": game,
        }
