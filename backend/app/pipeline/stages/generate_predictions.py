from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.prediction_pipeline_service import PredictionPipelineService


class GeneratePredictionsStage(PipelineStage):
    name = "Predictions Generated"
    dependencies = ("Simulations Executed",)

    def run(self, context: PipelineContext) -> PipelineResult:
        predictions = PredictionPipelineService().generate(context)
        context.predictions = predictions
        return PipelineResult(stage=self.name, success=True, processed_records=len(predictions), message="Predictions created")


def run(context: PipelineContext) -> PipelineResult:
    return GeneratePredictionsStage().run(context)
