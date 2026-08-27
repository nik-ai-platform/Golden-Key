"""add model runtime constraints

Revision ID: d4f8a2c71e90
Revises: b7e3a91c5d42
Create Date: 2026-08-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a2c71e90"
down_revision: Union[str, None] = "b7e3a91c5d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "uq_model_registry_sport_version"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "model_registry" not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("model_registry")
    }
    if CONSTRAINT_NAME in unique_constraints:
        return

    op.execute(
        sa.text(
            "WITH registry_state AS ("
            "SELECT sport, model_version, MAX(id) AS keeper_id, "
            "BOOL_OR(is_active) AS is_active, "
            "BOOL_OR(production_status) AS production_status "
            "FROM model_registry GROUP BY sport, model_version"
            ") "
            "UPDATE model_registry AS registry "
            "SET is_active = state.is_active, "
            "production_status = state.production_status "
            "FROM registry_state AS state "
            "WHERE registry.id = state.keeper_id"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM model_registry AS duplicate "
            "USING model_registry AS keeper "
            "WHERE duplicate.sport = keeper.sport "
            "AND duplicate.model_version = keeper.model_version "
            "AND duplicate.id < keeper.id"
        )
    )
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "model_registry",
        ["sport", "model_version"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "model_registry" not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("model_registry")
    }
    if CONSTRAINT_NAME in unique_constraints:
        op.drop_constraint(
            CONSTRAINT_NAME,
            "model_registry",
            type_="unique",
        )
