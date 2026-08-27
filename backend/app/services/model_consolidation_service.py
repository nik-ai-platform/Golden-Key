from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.model_consolidation import DEPRECATION_POLICY
from app.models.schema_deprecation import SchemaDeprecation


class ModelConsolidationService:
    def list_deprecations(self, db: Session | None = None) -> list[dict]:
        if db is None:
            return [
                {
                    "table_name": table_name,
                    "replacement_table": metadata.get("replacement_table"),
                    "status": metadata.get("status", "deprecated"),
                    "deprecated": True,
                    "notes": metadata.get("notes", ""),
                }
                for table_name, metadata in DEPRECATION_POLICY.items()
            ]

        try:
            rows = db.query(SchemaDeprecation).order_by(SchemaDeprecation.table_name.asc()).all()
        except SQLAlchemyError:
            return []

        return [
            {
                "table_name": row.table_name,
                "replacement_table": row.replacement_table,
                "status": row.status,
                "deprecated": bool(row.deprecated),
                "deprecated_at": row.deprecated_at.isoformat() if row.deprecated_at else None,
                "notes": row.notes,
            }
            for row in rows
        ]

    def is_deprecated(self, table_name: str, db: Session | None = None) -> bool:
        normalized = table_name.strip().lower()
        if db is None:
            return normalized in DEPRECATION_POLICY

        row = (
            db.query(SchemaDeprecation)
            .filter(SchemaDeprecation.table_name == normalized)
            .first()
        )
        return bool(row and row.deprecated)
