"""add prediction market snapshot

Revision ID: a4c6e8f102d3
Revises: e8a4c2d79f10
Create Date: 2026-08-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c6e8f102d3"
down_revision: Union[str, None] = "e8a4c2d79f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("line_value", sa.Float(), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("american_odds", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_predictions_game_model_market",
        "predictions",
        ["game_id", "model_version", "market"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_predictions_game_model_market",
        table_name="predictions",
    )
    op.drop_column("predictions", "american_odds")
    op.drop_column("predictions", "line_value")