from __future__ import annotations

from datetime import datetime, UTC
from typing import Any


class ResearchQueueService:
    def __init__(self) -> None:
        self._jobs: list[dict[str, Any]] = []
        self._next_id = 1

    def submit_request(self, request: dict[str, Any]) -> dict[str, Any]:
        job = {
            "id": self._next_id,
            "request": request,
            "status": "queued",
            "priority": request.get("priority", "normal"),
            "scheduled_at": datetime.now(UTC).isoformat(),
        }
        self._next_id += 1
        self._jobs.append(job)
        return job

    def list_jobs(self) -> list[dict[str, Any]]:
        return list(self._jobs)

    def run_next(self) -> dict[str, Any] | None:
        if not self._jobs:
            return None

        job = self._jobs[0]
        job["status"] = "running"
        job["status"] = "completed"
        return job
