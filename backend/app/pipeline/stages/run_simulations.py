from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.service_registry import ServiceRegistry


class RunSimulationsStage(PipelineStage):
    name = "Simulations Executed"
    dependencies = ("NPI Calculated",)

    def run(self, context: PipelineContext) -> PipelineResult:
        registry = ServiceRegistry()
        simulations = [registry.simulation.run(game) for game in context.games]
        context.simulations = simulations
        return PipelineResult(stage=self.name, success=True, processed_records=len(simulations), message="Simulations complete")


def run(context: PipelineContext) -> PipelineResult:
    return RunSimulationsStage().run(context)
