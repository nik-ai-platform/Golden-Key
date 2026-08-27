from __future__ import annotations

from typing import Any


class HypothesisGeneratorService:
    def generate_hypotheses(self, observations: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "observation": observations,
                "hypothesis": "Fade road favorites traveling 3+ time zones",
                "sport": observations.get("sport", "General"),
            },
            {
                "observation": observations,
                "hypothesis": "Back home underdogs with rest advantage when injury pressure rises",
                "sport": observations.get("sport", "General"),
            },
        ]
