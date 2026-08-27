from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_orchestrator import PipelineOrchestrator
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage


def test_pipeline_orchestrator_completes_daily_run():
    orchestrator = PipelineOrchestrator()
    result = orchestrator.run_daily_pipeline()

    assert result["status"] == "completed"
    assert result["pipeline_id"]
    assert len(result["stage_results"]) == 8
    assert all(stage["success"] for stage in result["stage_results"])


def test_pipeline_orchestrator_rolls_back_failed_stage():
    rollback_called = {"value": False}

    class PassingStage(PipelineStage):
        name = "Pass"

        def run(self, context: PipelineContext) -> PipelineResult:
            return PipelineResult(stage=self.name, success=True)

    class FailingStage(PipelineStage):
        name = "Fail"

        def run(self, context: PipelineContext) -> PipelineResult:
            return PipelineResult(stage=self.name, success=False, errors=["boom"])

        def rollback(self, context: PipelineContext) -> PipelineResult:
            rollback_called["value"] = True
            return PipelineResult(stage=self.name, success=True, message="rolled back")

    orchestrator = PipelineOrchestrator(stages=[PassingStage(), FailingStage()])
    result = orchestrator.run_daily_pipeline()

    assert result["status"] == "failed"
    assert result["failed_stage"] == "Fail"
    assert rollback_called["value"] is True
