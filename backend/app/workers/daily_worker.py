from __future__ import annotations

from app.services.daily_pipeline_service import DailyPipelineService


def run_daily_worker() -> dict:
    return DailyPipelineService().run_daily_workflow("06:00")
