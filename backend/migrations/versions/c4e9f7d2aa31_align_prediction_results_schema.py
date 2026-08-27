"""align prediction results schema

Revision ID: c4e9f7d2aa31
Revises: 87d7d9d66f10
Create Date: 2026-08-05 23:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4e9f7d2aa31"
down_revision: Union[str, None] = "87d7d9d66f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "prediction_results" in table_names:
        op.drop_table("prediction_results")

    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("actual_result", sa.String(), nullable=False),
        sa.Column("predicted_result", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("profit_loss", sa.Float(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.PrimaryKeyConstraint("id")
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "prediction_results" in table_names:
        op.drop_table("prediction_results")

    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("actual_winner", sa.String(), nullable=True),
        sa.Column("predicted_winner", sa.String(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("prediction_accuracy", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["prediction_id"], ["nik_scores.id"]),
        sa.PrimaryKeyConstraint("id")
    )