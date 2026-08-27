"""add market values table

Revision ID: e4c9a1b2d6f7
Revises: c7b2e4d1a9f0
Create Date: 2026-08-05 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4c9a1b2d6f7"
down_revision: Union[str, Sequence[str], None] = "c7b2e4d1a9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("market_type", sa.String(), nullable=False),
        sa.Column("model_projection", sa.Float(), nullable=True),
        sa.Column("market_line", sa.Float(), nullable=True),
        sa.Column("edge", sa.Float(), nullable=True),
        sa.Column("value_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_market_values_game_id", "market_values", ["game_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_values_game_id", table_name="market_values")
    op.drop_table("market_values")