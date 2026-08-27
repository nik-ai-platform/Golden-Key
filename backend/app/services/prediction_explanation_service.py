from __future__ import annotations

from typing import Any


class PredictionExplanationService:
    def generate_explanation(self, home_components: dict[str, Any], away_components: dict[str, Any], recommendation: str) -> dict[str, Any]:
        reasons: list[str] = []

        if home_components.get("strength", 0) > away_components.get("strength", 0):
            reasons.append("the home team has stronger season strength")
        else:
            reasons.append("the away team has stronger season strength")

        if home_components.get("form", 0) > away_components.get("form", 0):
            reasons.append("recent form favors the home side")
        else:
            reasons.append("recent form favors the away side")

        if home_components.get("offense_defense", 0) > away_components.get("offense_defense", 0):
            reasons.append("the matchup profile and defensive efficiency are favorable")
        else:
            reasons.append("the matchup profile and defensive efficiency are less favorable")

        return {
            "recommendation": recommendation,
            "reasons": reasons,
        }
