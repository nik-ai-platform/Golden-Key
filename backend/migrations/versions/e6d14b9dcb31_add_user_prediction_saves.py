"""add user prediction saves

Revision ID: e6d14b9dcb31
Revises: 884f0f552326
Create Date: 2026-08-05 22:18:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6d14b9dcb31"
down_revision: Union[str, None] = "884f0f552326"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_predictions" not in inspector.get_table_names():
        op.create_table(
            "user_predictions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("prediction_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "user_predictions" in inspector.get_table_names():
        op.drop_table("user_predictions")