from __future__ import annotations

from app.models.model_registry import ModelRegistry


class ModelRegistryService:
    """Tracks deployed model versions and their production status."""

    def list_models(self):
        return [
            {"name": "NPI", "status": "ACTIVE"},
            {"name": "Historical", "status": "ACTIVE"},
            {"name": "Market", "status": "ACTIVE"},
            {"name": "Situational", "status": "ACTIVE"},
            {"name": "Live", "status": "ACTIVE"},
        ]

    def create_registry_entry(self, model_name: str, sport: str, version: str, validation_score: float, production_status: bool = False) -> ModelRegistry:
        return ModelRegistry(
            model_name=model_name,
            model_version=version,
            sport=sport,
            version=version,
            validation_score=validation_score,
            production_status=production_status,
        )

    def latest_production_model(self, sport: str) -> ModelRegistry | None:
        return ModelRegistry(
            model_name=f"{sport}_Model_v1.3",
            model_version="1.3",
            sport=sport,
            version="1.3",
            validation_score=56.1,
            production_status=True,
        )
