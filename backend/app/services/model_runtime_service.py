from sqlalchemy.orm import Session

from app.services.production_model_service import ProductionModelService


class ModelRuntimeService:

    def __init__(self):
        self.production_models = ProductionModelService()

    def resolve(
        self,
        db: Session,
        sport: str,
    ) -> dict:

        version = self.production_models.get_active_version(
            db=db,
            sport=sport,
        )

        model = self.production_models.get_active_model(
            db=db,
            sport=sport,
        )

        return {
            "sport": sport,
            "model_version": version,
            "model": model,
        }
