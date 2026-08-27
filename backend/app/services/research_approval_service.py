from __future__ import annotations

from typing import Any


class ResearchApprovalService:
    stages = ["DISCOVERED", "TESTING", "VALIDATED", "REVIEW", "APPROVED", "AVAILABLE"]

    def advance(self, stage: str) -> str:
        try:
            index = self.stages.index(stage)
        except ValueError:
            return self.stages[0]

        return self.stages[min(index + 1, len(self.stages) - 1)]

    def review(self, payload: dict[str, Any]) -> dict[str, Any]:
        stage = payload.get("stage", "DISCOVERED")
        return {
            "stage": self.advance(stage),
            "approved": payload.get("approved", False),
            "notes": payload.get("notes", ""),
        }
