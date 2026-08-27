from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import engine
from app.services.model_consolidation_service import ModelConsolidationService


class SystemHealthService:
    def check(self) -> dict:
        database_status = "healthy"
        consolidation_status = "unavailable"
        deprecation_count = 0
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                result = connection.execute(text("SELECT COUNT(*) FROM schema_deprecations"))
                deprecation_count = int(result.scalar() or 0)
                consolidation_status = "enforced"
        except SQLAlchemyError:
            database_status = "unhealthy"
            fallback = ModelConsolidationService().list_deprecations()
            deprecation_count = len(fallback)
            consolidation_status = "policy_only"

        return {
            "database": database_status,
            "apis": "healthy",
            "models": "healthy",
            "ai_services": "healthy",
            "workers": "running",
            "data_feeds": "healthy",
            "pipeline": "running",
            "consolidation": consolidation_status,
            "deprecated_tables": deprecation_count,
        }
