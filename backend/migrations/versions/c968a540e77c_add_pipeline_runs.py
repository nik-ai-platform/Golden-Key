"""add pipeline runs

Revision ID: c968a540e77c
Revises: 288ee2ea9167
Create Date: 2026-08-05 12:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c968a540e77c"
down_revision: Union[str, Sequence[str], None] = "288ee2ea9167"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("id", sa.Integer(), nullable=True))

    op.execute("CREATE SEQUENCE IF NOT EXISTS pipeline_runs_id_seq OWNED BY pipeline_runs.id")
    op.execute("ALTER TABLE pipeline_runs ALTER COLUMN id SET DEFAULT nextval('pipeline_runs_id_seq')")
    op.execute("UPDATE pipeline_runs SET id = nextval('pipeline_runs_id_seq') WHERE id IS NULL")

    op.alter_column("pipeline_runs", "id", nullable=False)

    op.drop_constraint("pipeline_runs_pkey", "pipeline_runs", type_="primary")
    op.create_primary_key("pipeline_runs_pkey", "pipeline_runs", ["id"])

    op.drop_index("ix_pipeline_runs_run_id", table_name="pipeline_runs")

    op.drop_column("pipeline_runs", "run_id")
    op.drop_column("pipeline_runs", "start_time")
    op.drop_column("pipeline_runs", "end_time")
    op.drop_column("pipeline_runs", "stages_completed")
    op.drop_column("pipeline_runs", "records_processed")
    op.drop_column("pipeline_runs", "errors")

    op.add_column("pipeline_runs", sa.Column("games_processed", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("pipeline_runs", sa.Column("results", sa.Text(), nullable=True))
    op.add_column("pipeline_runs", sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_column("pipeline_runs", "created_at")
    op.drop_column("pipeline_runs", "results")
    op.drop_column("pipeline_runs", "games_processed")

    op.add_column("pipeline_runs", sa.Column("errors", sa.Text(), nullable=True))
    op.add_column("pipeline_runs", sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pipeline_runs", sa.Column("stages_completed", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pipeline_runs", sa.Column("end_time", sa.DateTime(), nullable=True))
    op.add_column("pipeline_runs", sa.Column("start_time", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column("pipeline_runs", sa.Column("run_id", sa.String(length=64), nullable=True))

    op.execute("UPDATE pipeline_runs SET run_id = 'run-' || id::text WHERE run_id IS NULL")
    op.alter_column("pipeline_runs", "run_id", nullable=False)

    op.drop_constraint("pipeline_runs_pkey", "pipeline_runs", type_="primary")
    op.create_primary_key("pipeline_runs_pkey", "pipeline_runs", ["run_id"])
    op.create_index("ix_pipeline_runs_run_id", "pipeline_runs", ["run_id"], unique=False)

    op.drop_column("pipeline_runs", "id")
    op.execute("DROP SEQUENCE IF EXISTS pipeline_runs_id_seq")
