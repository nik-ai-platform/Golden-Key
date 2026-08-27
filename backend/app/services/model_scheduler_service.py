from __future__ import annotations


class ModelSchedulerService:
    """A lightweight scheduler abstraction that queues jobs for later execution."""

    def __init__(self):
        self.jobs = []

    def enqueue_job(self, job_name: str) -> dict[str, str]:
        self.jobs.append({"name": job_name, "status": "queued"})
        return {"name": job_name, "status": "queued"}

    def run_pending_jobs(self) -> list[dict[str, str]]:
        for job in self.jobs:
            if job["status"] == "queued":
                job["status"] = "completed"
        return self.jobs
