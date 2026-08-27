from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.service_registry import ServiceRegistry


class ImportOddsStage(PipelineStage):
    name = "Odds Updated"
    dependencies = ("Games Imported",)

    def run(self, context: PipelineContext) -> PipelineResult:
        if not context.games:
            return PipelineResult(stage=self.name, success=False, errors=["No games available for odds import"])
        odds = ServiceRegistry().odds.import_odds(context.games)
        context.odds = odds
        return PipelineResult(stage=self.name, success=True, processed_records=len(odds), message="Odds synchronized")


def run(context: PipelineContext) -> PipelineResult:
    return ImportOddsStage().run(context)
