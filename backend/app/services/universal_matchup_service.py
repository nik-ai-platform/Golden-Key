from __future__ import annotations

from typing import Any


class UniversalMatchupService:
    def analyze_matchup(self, payload: dict[str, Any]) -> dict[str, Any]:
        team_a = payload.get("team_a", "Team A")
        team_b = payload.get("team_b", "Team B")

        return {
            "team_a": team_a,
            "team_b": team_b,
            "strength": {str(team_a): "Elite defense", str(team_b): "High pace offense"},
            "weakness": {str(team_a): "Turnovers under pressure", str(team_b): "Transition defense"},
            "style": {str(team_a): "Half-court control", str(team_b): "Tempo and spacing"},
            "environment": "Lower scoring environment",
            "historical_interaction": "Recent meetings trend to unders",
            "expected": "Lower scoring environment",
        }
