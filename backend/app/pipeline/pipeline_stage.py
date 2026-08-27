from __future__ import annotations

from abc import ABC, abstractmethod

from app.pipeline.pipeline_context import PipelineContext
from app.pipeline.pipeline_result import PipelineResult


class PipelineStage(ABC):
    name = "unnamed"
    dependencies: tuple[str, ...] = ()

    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineResult:
        raise NotImplementedError

    def rollback(self, context: PipelineContext) -> PipelineResult:
        return PipelineResult(stage=self.name, success=True, message="Rollback no-op")

    def health_check(self) -> PipelineResult:
        return PipelineResult(stage=self.name, success=True, message="healthy")
