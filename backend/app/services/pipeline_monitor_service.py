from __future__ import annotations

from datetime import UTC, datetime


class PipelineMonitorService:
    def __init__(self) -> None:
        self._runs: dict[str, dict] = {}

    def start_run(self, pipeline_id: str) -> None:
        self._runs[pipeline_id] = {
            "pipeline_id": pipeline_id,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "last_run": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "stages": [],
            "failures": 0,
            "retries": 0,
            "rows_processed": 0,
            "games_imported": 0,
            "predictions_generated": 0,
        }

    def record_stage(self, pipeline_id: str, stage: str, success: bool, duration_ms: float, processed_records: int) -> None:
        run = self._runs.get(pipeline_id)
        if not run:
            return
        run["stages"].append(
            {
                "stage": stage,
                "success": success,
                "duration_ms": duration_ms,
                "processed_records": processed_records,
            }
        )
        run["rows_processed"] += processed_records
        if stage == "Games Imported":
            run["games_imported"] = processed_records
        if stage == "Predictions Generated":
            run["predictions_generated"] = processed_records
        if not success:
            run["failures"] += 1

    def finish_run(self, pipeline_id: str, success: bool, errors: list[str]) -> None:
        run = self._runs.get(pipeline_id)
        if not run:
            return
        run["status"] = "completed" if success else "failed"
        run["completed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        run["errors"] = errors
        started_at = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00"))
        finished_at = datetime.fromisoformat(run["completed_at"].replace("Z", "+00:00"))
        run["duration_ms"] = round((finished_at - started_at).total_seconds() * 1000, 2)

    def dashboard_metrics(self) -> dict:
        runs = list(self._runs.values())
        if not runs:
            return {
                "pipeline_status": "idle",
                "last_run": None,
                "duration": None,
                "success_rate": 0,
                "failures": 0,
            }

        last = runs[-1]
        total = len(runs)
        successes = sum(1 for run in runs if run["status"] == "completed")
        failures = sum(1 for run in runs if run["status"] == "failed")
        return {
            "pipeline_status": last["status"],
            "last_run": last["last_run"],
            "duration": last.get("duration_ms"),
            "success_rate": round((successes / total) * 100, 1),
            "failures": failures,
        }
