"""add npi factor results and model versions

Revision ID: 9d12b4ac7f31
Revises: c4e9f7d2aa31
Create Date: 2026-08-06 00:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d12b4ac7f31"
down_revision: Union[str, None] = "c4e9f7d2aa31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "npi_factor_results" not in table_names:
        op.create_table(
            "npi_factor_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("prediction_id", sa.Integer(), nullable=False),
            sa.Column("factor_name", sa.String(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column("factor_score", sa.Float(), nullable=False),
            sa.Column("predicted_side", sa.String(), nullable=True),
            sa.Column("actual_outcome", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "model_versions" not in table_names:
        op.create_table(
            "model_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("model_name", sa.String(length=128), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("overall_accuracy", sa.Float(), nullable=True),
            sa.Column("ats_accuracy", sa.Float(), nullable=True),
            sa.Column("changes", sa.Text(), nullable=True),
            sa.Column("performance", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="Testing"),
            sa.Column("approved_by", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_model_versions_id", "model_versions", ["id"], unique=False)
    else:
        columns = {column["name"] for column in inspector.get_columns("model_versions")}
        if "notes" not in columns:
            op.add_column("model_versions", sa.Column("notes", sa.Text(), nullable=True))
        if "overall_accuracy" not in columns:
            op.add_column("model_versions", sa.Column("overall_accuracy", sa.Float(), nullable=True))
        if "ats_accuracy" not in columns:
            op.add_column("model_versions", sa.Column("ats_accuracy", sa.Float(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "npi_factor_results" in table_names:
        op.drop_table("npi_factor_results")

    if "model_versions" in table_names:
        columns = {column["name"] for column in inspector.get_columns("model_versions")}
        if "ats_accuracy" in columns:
            op.drop_column("model_versions", "ats_accuracy")
        if "overall_accuracy" in columns:
            op.drop_column("model_versions", "overall_accuracy")
        if "notes" in columns:
            op.drop_column("model_versions", "notes")