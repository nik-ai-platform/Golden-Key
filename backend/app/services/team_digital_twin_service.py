from __future__ import annotations

from typing import Any


class TeamDigitalTwinService:
    def build_twin(self, team: dict[str, Any]) -> dict[str, Any]:
        return {
            "team": team.get("name", "Unknown Team"),
            "offense": 92,
            "defense": 88,
            "clutch": 95,
            "health": 84,
            "inputs": {
                "historical_performance": team.get("historical_performance"),
                "current_roster": team.get("current_roster"),
                "injuries": team.get("injuries"),
                "coaching": team.get("coaching"),
                "schedule": team.get("schedule"),
                "opponent_matchups": team.get("opponent_matchups"),
            },
        }
