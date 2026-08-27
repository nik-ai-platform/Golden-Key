"""add pipeline runs table

Revision ID: d9e7f1a2c4b0
Revises: a12d4b8f9c30
Create Date: 2026-08-05 18:05:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9e7f1a2c4b0"
down_revision: Union[str, Sequence[str], None] = "a12d4b8f9c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stages_completed", sa.Integer(), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_pipeline_runs_run_id"), "pipeline_runs", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pipeline_runs_run_id"), table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
