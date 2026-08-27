from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistry
from app.models.model_version import ModelVersion
from app.services.npi_weight_profile_service import NPIWeightProfileService


class ModelBootstrapService:

    DEFAULT_VERSION = "NPI-4.0"
    MODEL_NAME = "Nik Power Index"

    SPORTS = (
        "NFL",
        "NBA",
        "NCAAF",
        "NCAAB",
        "WNBA",
    )

    BASELINE_WEIGHTS = {
        "home_advantage": 20,
        "spread_value": 35,
        "market_environment": 25,
        "situational_edge": 40,
        "historical_rules": 80,
    }

    def __init__(self) -> None:
        self.weight_profiles = NPIWeightProfileService()

    def bootstrap_all(self, db: Session) -> dict:
        results = [
            self.bootstrap_sport(
                db=db,
                sport=sport,
                model_version=self.DEFAULT_VERSION,
            )
            for sport in self.SPORTS
        ]
        return {
            "model_version": self.DEFAULT_VERSION,
            "sports_processed": len(results),
            "results": results,
        }

    def bootstrap_sport(
        self,
        db: Session,
        sport: str,
        model_version: str | None = None,
    ) -> dict:
        sport = sport.upper()
        if sport not in self.SPORTS:
            raise ValueError(f"Unsupported sport: {sport}")

        version = model_version or self.DEFAULT_VERSION
        model = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.version == version,
                ModelVersion.sport == sport,
            )
            .first()
        )
        if not model:
            model = ModelVersion(
                model_name=self.MODEL_NAME,
                version=version,
                sport=sport,
                status="production",
                games_evaluated=0,
                notes="Initial production bootstrap",
            )
            db.add(model)
        else:
            model.status = "production"

        active_entries = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.sport == sport,
                ModelRegistry.is_active.is_(True),
            )
            .all()
        )
        for entry in active_entries:
            if entry.model_version != version:
                entry.is_active = False
                entry.production_status = False
                old_model = (
                    db.query(ModelVersion)
                    .filter(
                        ModelVersion.version == entry.model_version,
                        ModelVersion.sport == sport,
                    )
                    .first()
                )
                if old_model:
                    old_model.status = "inactive"

        registry = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.sport == sport,
                ModelRegistry.model_version == version,
            )
            .first()
        )
        if not registry:
            registry = ModelRegistry(
                model_name=self.MODEL_NAME,
                model_version=version,
                sport=sport,
                version=version,
                is_active=True,
                production_status=True,
            )
            db.add(registry)
        else:
            registry.model_name = self.MODEL_NAME
            registry.version = version
            registry.is_active = True
            registry.production_status = True

        db.flush()
        profile_created = False
        try:
            weights = self.weight_profiles.get_profile(
                db=db,
                sport=sport,
                model_version=version,
            )
        except ValueError:
            profile_created = True
            self.weight_profiles.create_profile(
                db=db,
                sport=sport,
                model_version=version,
                weights=self.BASELINE_WEIGHTS,
            )
            weights = dict(self.BASELINE_WEIGHTS)

        db.commit()
        return {
            "sport": sport,
            "model_version": version,
            "status": "production",
            "registry_active": True,
            "profile_created": profile_created,
            "weight_total": sum(weights.values()),
        }
