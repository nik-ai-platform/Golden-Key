"""add settlement constraints

Revision ID: e8a4c2d79f10
Revises: f6c2b8a41d73
Create Date: 2026-08-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8a4c2d79f10"
down_revision: Union[str, None] = "f6c2b8a41d73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "prediction_results"
CONSTRAINT_NAME = "uq_prediction_result_prediction"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    if CONSTRAINT_NAME in unique_constraints:
        return

    op.execute(
        sa.text(
            "DELETE FROM prediction_results AS duplicate "
            "USING prediction_results AS keeper "
            "WHERE duplicate.prediction_id = keeper.prediction_id "
            "AND duplicate.id > keeper.id"
        )
    )
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        ["prediction_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    if CONSTRAINT_NAME in unique_constraints:
        op.drop_constraint(
            CONSTRAINT_NAME,
            TABLE_NAME,
            type_="unique",
        )
