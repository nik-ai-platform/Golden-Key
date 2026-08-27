from __future__ import annotations

from typing import Any


class AIMemoryService:
    def __init__(self) -> None:
        self.preferences: dict[str, Any] = {}
        self.historical_questions: list[str] = []
        self.feedback: list[dict[str, Any]] = []

    def store_preferences(self, user: Any, message: str, response: str) -> None:
        profile = getattr(user, "profile", None) if user else None
        if profile is None:
            profile = {}

        self.preferences.update(
            {
                "favorite_sports": profile.get("favorite_sports", ["NBA", "NCAAB"]),
                "risk_tolerance": profile.get("risk_level", "Moderate"),
                "betting_style": profile.get("betting_style", "underdog value"),
                "historical_questions": self.historical_questions + [message],
            }
        )
        self.historical_questions.append(message)

    def get_memory(self) -> dict[str, Any]:
        return {
            "preferences": self.preferences,
            "historical_questions": self.historical_questions,
            "feedback": self.feedback,
        }
