from __future__ import annotations

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult
from app.pipeline.pipeline_stage import PipelineStage
from app.services.data_validation_service import DataValidationService


class ValidateDataStage(PipelineStage):
    name = "Data Validated"
    dependencies = ("Games Imported", "Odds Updated")

    def run(self, context: PipelineContext) -> PipelineResult:
        validation = DataValidationService().validate(context.games, context.odds)
        if not validation["valid"]:
            return PipelineResult(stage=self.name, success=False, errors=validation["errors"], warnings=validation["warnings"])
        return PipelineResult(stage=self.name, success=True, warnings=validation["warnings"], message="Validation successful")


def run(context: PipelineContext) -> PipelineResult:
    return ValidateDataStage().run(context)
