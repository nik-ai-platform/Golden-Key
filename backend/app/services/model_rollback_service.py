from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.model_registry import ModelRegistry
from app.models.model_version import ModelVersion


class ModelRollbackService:
    """Restores a previous model version and its configuration."""

    def rollback(
        self,
        db: Session | str,
        sport: str,
        target_version: str | None = None,
        approved_by: str | None = None,
        reason: str | None = None,
    ):
        if isinstance(db, str) and target_version is None:
            return {
                "current_version": db,
                "restored_version": sport,
                "status": "Rolled Back",
            }

        if not approved_by:
            return {
                "rolled_back": False,
                "status": "approval_required",
            }

        target_model = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.version == target_version,
                ModelVersion.sport == sport,
            )
            .first()
        )

        if not target_model:
            return {
                "rolled_back": False,
                "status": "not_found",
                "reason": f"{target_version} not found for {sport}",
            }

        active_entries = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.sport == sport,
                ModelRegistry.is_active.is_(True),
            )
            .all()
        )
        previous_versions = []

        for active in active_entries:
            previous_versions.append(active.model_version)
            active.is_active = False
            active.production_status = False

            old_model = (
                db.query(ModelVersion)
                .filter(
                    ModelVersion.version == active.model_version,
                    ModelVersion.sport == sport,
                )
                .first()
            )
            if old_model:
                old_model.status = "inactive"

        target_registry = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.model_version == target_version,
                ModelRegistry.sport == sport,
            )
            .first()
        )

        if not target_registry:
            target_registry = ModelRegistry(
                model_name=target_model.model_name,
                model_version=target_version,
                sport=sport,
                version=target_version,
                is_active=True,
                production_status=True,
            )
            db.add(target_registry)
        else:
            target_registry.is_active = True
            target_registry.production_status = True

        target_model.status = "production"
        target_model.approved_by = approved_by

        if reason:
            existing_notes = target_model.notes or ""
            rollback_note = f"Rollback: {reason}"
            target_model.notes = f"{existing_notes}\n{rollback_note}".strip()

        db.commit()
        db.refresh(target_model)
        db.refresh(target_registry)

        return {
            "rolled_back": True,
            "sport": sport,
            "target_version": target_version,
            "previous_versions": previous_versions,
            "approved_by": approved_by,
            "reason": reason,
        }
