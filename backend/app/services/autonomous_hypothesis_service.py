from __future__ import annotations

from typing import Any


class AutonomousHypothesisService:
    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        observation = str(data.get("observation", "Road favorites declining"))
        possible_cause = str(
            data.get(
                "possible_cause",
                "Travel fatigue and recovery mismatches after timezone changes",
            )
        )
        hypothesis = str(
            data.get(
                "hypothesis",
                "Travel fatigue reduces favorite performance after timezone changes.",
            )
        )
        experiment = {
            "dataset": data.get("dataset", "NBA games, last 5 seasons"),
            "segments": ["timezone change", "rest disadvantage", "road favorite"],
            "metric": "ATS delta and ROI",
            "sample_target": int(data.get("sample_target", 15000) or 15000),
        }

        return {
            "observation": observation,
            "possible_cause": possible_cause,
            "testable_hypothesis": hypothesis,
            "experiment_design": experiment,
        }
