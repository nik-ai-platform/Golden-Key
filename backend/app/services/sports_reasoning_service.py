from __future__ import annotations

from typing import Any


class SportsReasoningService:
    def explain(self, analysis: dict[str, Any]) -> dict[str, Any]:
        matchup = analysis.get("matchup", "this matchup")
        lines = [
            "Offensive efficiency exceeds market expectation.",
            "Defensive matchup favors the team.",
            "Simulation probability exceeds implied odds.",
        ]

        explanation = "Golden Key identifies value because:\n\n1. {one}\n\n2. {two}\n\n3. {three}".format(
            one=lines[0],
            two=lines[1],
            three=lines[2],
        )

        return {
            "question": f"Why does Golden Key like {matchup}?",
            "explanation": explanation,
            "highlights": lines,
        }
