from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.service_registry import ServiceRegistry


class CalculateNPIStage(PipelineStage):
    name = "NPI Calculated"
    dependencies = ("Features Generated",)

    def run(self, context: PipelineContext) -> PipelineResult:
        registry = ServiceRegistry()
        npi_scores = []
        for game, odds in zip(context.games, context.odds):
            score = registry.npi.calculate(game, odds)
            npi_scores.append({"game_id": game["id"], "npi_score": score})
        context.npi_scores = npi_scores
        return PipelineResult(stage=self.name, success=True, processed_records=len(npi_scores), message="NPI scores computed")


def run(context: PipelineContext) -> PipelineResult:
    return CalculateNPIStage().run(context)
