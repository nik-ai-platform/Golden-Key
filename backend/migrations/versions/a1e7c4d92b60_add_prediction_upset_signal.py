"""add prediction upset signal

Revision ID: a1e7c4d92b60
Revises: f4a9c2e71d30
Create Date: 2026-09-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1e7c4d92b60"
down_revision: Union[str, None] = "f4a9c2e71d30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("upset_signal", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("predictions", "upset_signal")