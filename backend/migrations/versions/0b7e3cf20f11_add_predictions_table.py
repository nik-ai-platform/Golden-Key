"""add predictions table

Revision ID: 0b7e3cf20f11
Revises: f2c1b8a44e91
Create Date: 2026-08-05 23:18:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b7e3cf20f11"
down_revision: Union[str, Sequence[str], None] = "f2c1b8a44e91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("selection", sa.String(), nullable=False),
        sa.Column("npi_score", sa.Float(), nullable=False),
        sa.Column("win_probability", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("projected_edge", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("reasoning", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_predictions_id"), "predictions", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_predictions_id"), table_name="predictions")
    op.drop_table("predictions")
