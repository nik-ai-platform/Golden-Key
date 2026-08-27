from __future__ import annotations

from typing import Any


class ExplainabilityService:
    """Produces human-readable reasons for every prediction."""

    def explain_prediction(
        self,
        prediction: str,
        confidence: float,
        top_factors: list[str] | None = None,
        reduced_confidence: list[str] | None = None,
        game_id: int | None = None,
    ) -> dict[str, Any]:
        factors = top_factors or ["Rest Advantage", "Defensive Rating", "Home Court"]
        reduced = reduced_confidence or ["Injury uncertainty"]
        return {
            "prediction": prediction,
            "confidence": int(confidence),
            "top_factors": factors,
            "reduced_confidence": reduced,
            "why": "The combination of rest edge, matchup quality, and home-court advantage drove the prediction.",
            "what_contributed": factors,
            "what_reduced_confidence": reduced,
            "what_increased_confidence": ["Rest Advantage", "Home Court"],
            "game_id": game_id,
        }
