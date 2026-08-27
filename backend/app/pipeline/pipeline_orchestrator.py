from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from app.core.logging import logger
from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.stages.calculate_npi import CalculateNPIStage
from app.pipeline.stages.generate_features import GenerateFeaturesStage
from app.pipeline.stages.generate_predictions import GeneratePredictionsStage
from app.pipeline.stages.import_games import ImportGamesStage
from app.pipeline.stages.import_odds import ImportOddsStage
from app.pipeline.stages.publish_results import PublishResultsStage
from app.pipeline.stages.run_simulations import RunSimulationsStage
from app.pipeline.stages.validate_data import ValidateDataStage
from app.services.pipeline_monitor_service import PipelineMonitorService


class PipelineOrchestrator:
    def __init__(self, stages: Iterable | None = None) -> None:
        self.monitor = PipelineMonitorService()
        self.context: PipelineContext | None = None
        self.failed_stage = None
        self.stages = list(
            stages
            or [
                ImportGamesStage(),
                ImportOddsStage(),
                ValidateDataStage(),
                GenerateFeaturesStage(),
                CalculateNPIStage(),
                RunSimulationsStage(),
                GeneratePredictionsStage(),
                PublishResultsStage(),
            ]
        )

    def run_daily_pipeline(self) -> dict:
        context = PipelineContext()
        self.context = context
        self.monitor.start_run(context.pipeline_id)
        logger.info("Pipeline Started | pipeline_id=%s", context.pipeline_id)

        for stage in self.stages:
            result = self.execute_stage(stage)
            context.stage_results.append(
                {
                    "stage": result.stage,
                    "success": result.success,
                    "processed_records": result.processed_records,
                    "warnings": result.warnings,
                    "errors": result.errors,
                    "message": result.message,
                }
            )
            if not result.success:
                self.failed_stage = stage
                self.monitor.finish_run(context.pipeline_id, False, result.errors)
                self.rollback_failed_stage()
                return {
                    "pipeline_id": context.pipeline_id,
                    "status": "failed",
                    "failed_stage": result.stage,
                    "errors": result.errors,
                    "stage_results": context.stage_results,
                }

        completed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        context.metadata["completed_at"] = completed_at
        self.monitor.finish_run(context.pipeline_id, True, [])
        logger.info("Pipeline Complete | pipeline_id=%s", context.pipeline_id)
        return {
            "pipeline_id": context.pipeline_id,
            "status": "completed",
            "stage_results": context.stage_results,
            "predictions": context.predictions,
            "reports": context.reports,
        }

    def execute_stage(self, stage) -> PipelineResult:
        if self.context is None:
            self.context = PipelineContext()
        logger.info("%s | pipeline_id=%s", stage.name, self.context.pipeline_id)
        started_at = datetime.now(UTC)
        result = stage.run(self.context)
        duration_ms = round((datetime.now(UTC) - started_at).total_seconds() * 1000, 2)
        self.monitor.record_stage(self.context.pipeline_id, result.stage, result.success, duration_ms, result.processed_records)
        return result

    def rollback_failed_stage(self):
        if self.context is None or self.failed_stage is None:
            return PipelineResult(stage="rollback", success=False, message="No failed stage to rollback")

        rollback_result = self.failed_stage.rollback(self.context)
        logger.error("Pipeline Failure | pipeline_id=%s | stage=%s", self.context.pipeline_id, self.failed_stage.name)
        return rollback_result
