from __future__ import annotations

from typing import Any


class AIPersonaService:
    def get_personas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "The Analyst",
                "focus": ["Statistics", "Trends", "Models"],
            },
            {
                "name": "The Scout",
                "focus": ["Matchups", "Players", "Team Identity"],
            },
            {
                "name": "The Trader",
                "focus": ["Market", "Value", "Risk"],
            },
            {
                "name": "The Researcher",
                "focus": ["Discovery", "Experiments", "Patterns"],
            },
        ]

    def assign_for_question(self, question: str) -> dict[str, Any]:
        lower = question.lower()
        personas = self.get_personas()

        if "market" in lower or "value" in lower or "odds" in lower:
            selected = personas[2]
        elif "matchup" in lower or "player" in lower:
            selected = personas[1]
        elif "discover" in lower or "experiment" in lower:
            selected = personas[3]
        else:
            selected = personas[0]

        return {
            "question": question,
            "persona": selected,
        }
