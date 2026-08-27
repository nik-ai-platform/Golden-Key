"""add ai analysis table

Revision ID: 288ee2ea9167
Revises: 6f4f2c0a9d21
Create Date: 2026-08-06 00:15:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "288ee2ea9167"
down_revision: Union[str, Sequence[str], None] = "6f4f2c0a9d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ai_analysis")
