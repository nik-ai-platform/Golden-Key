"""add simulation columns to predictions

Revision ID: 6f4f2c0a9d21
Revises: 0b7e3cf20f11
Create Date: 2026-08-05 23:58:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f4f2c0a9d21"
down_revision: Union[str, Sequence[str], None] = "0b7e3cf20f11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("simulation_probability", sa.Float(), nullable=True))
    op.add_column("predictions", sa.Column("simulation_runs", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("simulation_margin", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("predictions", "simulation_margin")
    op.drop_column("predictions", "simulation_runs")
    op.drop_column("predictions", "simulation_probability")
