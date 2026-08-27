from __future__ import annotations

from typing import Any


class DiscoveryMemoryService:
    def __init__(self) -> None:
        self._memory: list[dict[str, Any]] = []

    def store(self, entry: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "question": entry.get("question", ""),
            "experiment": entry.get("experiment", ""),
            "result": entry.get("result", ""),
            "lesson": entry.get("lesson", ""),
        }
        self._memory.append(payload)
        return payload

    def should_deprioritize(self, question: str) -> bool:
        normalized = question.strip().lower()
        for item in self._memory:
            stored_question = str(item.get("question", "")).strip().lower()
            result = str(item.get("result", "")).strip().lower()
            if stored_question == normalized and ("no meaningful edge" in result or "failed" in result):
                return True
        return False

    def list_entries(self) -> list[dict[str, Any]]:
        return list(self._memory)
