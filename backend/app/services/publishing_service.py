from __future__ import annotations

from typing import Any

from app.pipeline.pipeline_context import PipelineContext


class PublishingService:
    def publish(self, context: PipelineContext) -> dict[str, Any]:
        if not context.predictions:
            return {"published": False, "errors": ["No predictions available"]}

        reports = [
            {
                "headline": "Daily Pipeline",
                "status": "Healthy",
                "games_imported": len(context.games),
                "predictions_generated": len(context.predictions),
                "runtime": context.metadata.get("duration", "unknown"),
            }
        ]
        return {
            "published": True,
            "dashboard": True,
            "api": True,
            "reports": reports,
            "notifications": ["New Prediction", "Portfolio Alert"],
        }
