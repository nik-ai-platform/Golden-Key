from __future__ import annotations

from datetime import UTC, datetime

from app.pipeline.pipeline_orchestrator import PipelineOrchestrator


class PipelineScheduler:
    def __init__(self) -> None:
        self.orchestrator = PipelineOrchestrator()

    def run_daily_execution(self) -> dict:
        return self.orchestrator.run_daily_pipeline()

    def run_manual_execution(self) -> dict:
        return self.orchestrator.run_daily_pipeline()

    def run_recovery_execution(self) -> dict:
        return self.orchestrator.run_daily_pipeline()

    def weekend_scheduling(self) -> dict:
        return {
            "schedule": "weekend",
            "time": "07:30",
            "stages": ["Games", "Odds", "Models", "Predictions", "Publish"],
        }

    def sport_specific_scheduling(self, sport: str) -> dict:
        slot = "05:00" if sport.upper() in {"NBA", "NCAAB"} else "06:00"
        return {
            "sport": sport,
            "scheduled_time": slot,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
