from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.publishing_service import PublishingService


class PublishResultsStage(PipelineStage):
    name = "Predictions Published"
    dependencies = ("Predictions Generated",)

    def run(self, context: PipelineContext) -> PipelineResult:
        publication = PublishingService().publish(context)
        if not publication["published"]:
            return PipelineResult(stage=self.name, success=False, errors=publication.get("errors", ["Publishing failed"]))
        context.reports = publication.get("reports", [])
        return PipelineResult(stage=self.name, success=True, processed_records=len(context.reports), message="Publishing completed")


def run(context: PipelineContext) -> PipelineResult:
    return PublishResultsStage().run(context)
