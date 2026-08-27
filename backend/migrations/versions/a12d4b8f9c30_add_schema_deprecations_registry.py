"""add schema deprecations registry

Revision ID: a12d4b8f9c30
Revises: e4c9a1b2d6f7
Create Date: 2026-08-05 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a12d4b8f9c30"
down_revision: Union[str, Sequence[str], None] = "e4c9a1b2d6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schema_deprecations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("replacement_table", sa.String(length=128), nullable=True),
        sa.Column("deprecated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deprecated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("removal_after", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="deprecated"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_schema_deprecations_id", "schema_deprecations", ["id"], unique=False)
    op.create_index("ix_schema_deprecations_table_name", "schema_deprecations", ["table_name"], unique=True)

    table = sa.table(
        "schema_deprecations",
        sa.column("table_name", sa.String),
        sa.column("replacement_table", sa.String),
        sa.column("deprecated", sa.Boolean),
        sa.column("status", sa.String),
        sa.column("notes", sa.Text),
    )

    op.bulk_insert(
        table,
        [
            {
                "table_name": "prediction_results",
                "replacement_table": "predictions_unified",
                "deprecated": True,
                "status": "deprecated",
                "notes": "Use unified prediction output records.",
            },
            {
                "table_name": "prediction_evaluations",
                "replacement_table": "prediction_outcomes",
                "deprecated": True,
                "status": "deprecated",
                "notes": "Use outcome tracking and analytics snapshots.",
            },
            {
                "table_name": "prediction_history",
                "replacement_table": "predictions_unified",
                "deprecated": True,
                "status": "deprecated",
                "notes": "History can be reconstructed from snapshots/outcomes.",
            },
            {
                "table_name": "research_agent_jobs",
                "replacement_table": "research_tasks",
                "deprecated": True,
                "status": "deprecated",
                "notes": "Use autonomous research task schema.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_schema_deprecations_table_name", table_name="schema_deprecations")
    op.drop_index("ix_schema_deprecations_id", table_name="schema_deprecations")
    op.drop_table("schema_deprecations")
