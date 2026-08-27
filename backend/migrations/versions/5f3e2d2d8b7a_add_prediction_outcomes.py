"""add prediction outcomes

Revision ID: 5f3e2d2d8b7a
Revises: 33e44d249706
Create Date: 2026-07-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f3e2d2d8b7a"
down_revision: Union[str, Sequence[str], None] = "33e44d249706"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "prediction_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("predicted_winner", sa.String(), nullable=False),
        sa.Column("actual_winner", sa.String(), nullable=False),
        sa.Column("predicted_confidence", sa.Float(), nullable=False),
        sa.Column("prediction_correct", sa.Boolean(), nullable=False),
        sa.Column("point_spread_error", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["prediction_id"], ["nik_scores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id", name="uq_prediction_outcomes_prediction_id"),
    )
    op.create_index(
        "ix_prediction_outcomes_created_at",
        "prediction_outcomes",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_prediction_outcomes_game_id",
        "prediction_outcomes",
        ["game_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_prediction_outcomes_game_id", table_name="prediction_outcomes")
    op.drop_index("ix_prediction_outcomes_created_at", table_name="prediction_outcomes")
    op.drop_table("prediction_outcomes")
