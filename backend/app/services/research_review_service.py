from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class ResearchReviewService:
    def __init__(self) -> None:
        self._queue: list[dict[str, Any]] = []

    def enqueue(self, recommendation: dict[str, Any]) -> dict[str, Any]:
        item = {
            "id": len(self._queue) + 1,
            "status": "pending_review",
            "workflow": [
                "AI Discovery",
                "Experiment Complete",
                "Recommendation Created",
                "Human Review",
                "Approve / Reject",
                "Deploy",
            ],
            "submitted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "recommendation": recommendation,
        }
        self._queue.append(item)
        return item

    def review(self, review_payload: dict[str, Any]) -> dict[str, Any]:
        item_id = int(review_payload.get("id", 0) or 0)
        decision = str(review_payload.get("decision", "reject")).lower()

        for item in self._queue:
            if item["id"] == item_id:
                approved = decision == "approve"
                item["status"] = "approved" if approved else "rejected"
                item["reviewed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                item["deploy"] = "ready" if approved else "blocked"
                return item

        return {
            "id": item_id,
            "status": "not_found",
            "deploy": "blocked",
        }

    def list_queue(self) -> list[dict[str, Any]]:
        return list(self._queue)
