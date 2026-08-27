from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.service_registry import ServiceRegistry


class ImportGamesStage(PipelineStage):
    name = "Games Imported"

    def run(self, context: PipelineContext) -> PipelineResult:
        games = ServiceRegistry().game.import_today_games()
        context.games = games
        return PipelineResult(stage=self.name, success=True, processed_records=len(games), message="Games imported")


def run(context: PipelineContext) -> PipelineResult:
    return ImportGamesStage().run(context)
