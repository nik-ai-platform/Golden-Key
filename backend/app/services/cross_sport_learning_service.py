from __future__ import annotations

from typing import Any


class CrossSportLearningService:
    def transfer_patterns(self) -> dict[str, Any]:
        mapping = {
            "NFL": "Rest disadvantage",
            "NBA": "Travel fatigue",
            "NCAAB": "Schedule compression",
        }
        insight = "Physical fatigue impacts performance across sports."
        return {
            "patterns": mapping,
            "insight": insight,
        }

    def compare_sports(self, sport_a: str, sport_b: str) -> dict[str, Any]:
        baseline = self.transfer_patterns()["patterns"]
        return {
            "sport_a": sport_a,
            "sport_b": sport_b,
            "driver_a": baseline.get(sport_a, "Unknown"),
            "driver_b": baseline.get(sport_b, "Unknown"),
            "shared_factor": "fatigue management",
        }

    def learn(self, feature_name, sport, transfer_allowed):
        if transfer_allowed:
            return {
                "feature": feature_name,
                "sport": sport,
                "status": "accepted",
                "message": f"Feature {feature_name} transferred to {sport}",
            }
        return {
            "feature": feature_name,
            "sport": sport,
            "status": "rejected",
            "message": f"NBA feature {feature_name} was not approved for NFL transfer",
        }
