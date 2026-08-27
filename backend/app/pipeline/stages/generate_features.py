from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.feature_pipeline_service import FeaturePipelineService


class GenerateFeaturesStage(PipelineStage):
    name = "Features Generated"
    dependencies = ("Data Validated",)

    def run(self, context: PipelineContext) -> PipelineResult:
        features = FeaturePipelineService().generate(context.games, context.odds)
        context.features = features
        return PipelineResult(stage=self.name, success=True, processed_records=len(features), message="Feature vectors generated")


def run(context: PipelineContext) -> PipelineResult:
    return GenerateFeaturesStage().run(context)
