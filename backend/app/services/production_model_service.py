from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistry
from app.models.model_version import ModelVersion


class ProductionModelService:

    def get_active_registry_entry(
        self,
        db: Session,
        sport: str,
    ) -> ModelRegistry | None:

        return (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.sport == sport,
                ModelRegistry.is_active.is_(True),
            )
            .order_by(ModelRegistry.id.desc())
            .first()
        )

    def get_active_version(
        self,
        db: Session,
        sport: str,
    ) -> str:

        registry_entry = self.get_active_registry_entry(
            db=db,
            sport=sport,
        )

        if registry_entry:
            return registry_entry.model_version

        model_version = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.sport == sport,
                ModelVersion.status == "production",
            )
            .order_by(ModelVersion.id.desc())
            .first()
        )

        if model_version:
            return model_version.version

        raise ValueError(
            f"No production model configured for sport: {sport}"
        )

    def get_active_model(
        self,
        db: Session,
        sport: str,
    ) -> ModelVersion | None:

        version = self.get_active_version(
            db=db,
            sport=sport,
        )

        return (
            db.query(ModelVersion)
            .filter(
                ModelVersion.version == version,
                ModelVersion.sport == sport,
            )
            .first()
        )
