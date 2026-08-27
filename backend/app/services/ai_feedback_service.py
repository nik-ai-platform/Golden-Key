from __future__ import annotations

from typing import Any


class AIFeedbackService:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def record_feedback(self, helpful: bool, correct: bool, user_followed: bool, outcome: str) -> dict[str, Any]:
        entry = {
            "helpful": helpful,
            "correct": correct,
            "user_followed": user_followed,
            "outcome": outcome,
        }
        self.entries.append(entry)
        return entry
