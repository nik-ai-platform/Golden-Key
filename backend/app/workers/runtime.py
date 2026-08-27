from __future__ import annotations

import os
import time
from datetime import UTC, datetime

from app.database.session import SessionLocal
from app.scheduler.job_scheduler import JobScheduler
from app.services.pipeline_scheduler import PipelineScheduler
from app.workers.daily_worker import run_daily_worker
from app.workers.learning_worker import run_learning_worker


def _interval_seconds() -> int:
    value = os.getenv("WORKER_INTERVAL_SECONDS", "300")
    try:
        return max(30, int(value))
    except ValueError:
        return 300


def run_worker_loop() -> None:
    interval = _interval_seconds()
    while True:
        started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        run_learning_worker()
        run_daily_worker()
        print(f"[worker] completed batch at {started}", flush=True)
        time.sleep(interval)


def run_scheduler_loop() -> None:
    interval = _interval_seconds()
    scheduler = JobScheduler()
    pipeline_scheduler = PipelineScheduler()

    while True:
        started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        db = SessionLocal()
        try:
            scheduler.run(db)
            pipeline_scheduler.run_daily_execution()
            print(f"[scheduler] completed cycle at {started}", flush=True)
        finally:
            db.close()
        time.sleep(interval)


def main() -> None:
    mode = os.getenv("RUNTIME_MODE", "worker").strip().lower()
    if mode == "scheduler":
        run_scheduler_loop()
        return

    run_worker_loop()


if __name__ == "__main__":
    main()