"""add npi weight profiles

Revision ID: f6c2b8a41d73
Revises: d4f8a2c71e90
Create Date: 2026-08-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6c2b8a41d73"
down_revision: Union[str, None] = "d4f8a2c71e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "npi_weight_profiles"


BASELINE_WEIGHTS = (
    ("home_advantage", 20.0),
    ("spread_value", 35.0),
    ("market_environment", 25.0),
    ("situational_edge", 40.0),
    ("historical_rules", 80.0),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABLE_NAME not in inspector.get_table_names():
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("sport", sa.String(), nullable=False),
            sa.Column("model_version", sa.String(), nullable=False),
            sa.Column("factor_name", sa.String(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "sport",
                "model_version",
                "factor_name",
                name="uq_npi_weight_profile_factor",
            ),
        )
        op.create_index(
            op.f("ix_npi_weight_profiles_id"),
            TABLE_NAME,
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_npi_weight_profiles_sport"),
            TABLE_NAME,
            ["sport"],
            unique=False,
        )
        op.create_index(
            op.f("ix_npi_weight_profiles_model_version"),
            TABLE_NAME,
            ["model_version"],
            unique=False,
        )

    inspector = sa.inspect(bind)
    if "model_registry" not in inspector.get_table_names():
        return

    for factor_name, weight in BASELINE_WEIGHTS:
        op.execute(
            sa.text(
                "INSERT INTO npi_weight_profiles "
                "(sport, model_version, factor_name, weight, is_active) "
                "SELECT UPPER(registry.sport), registry.model_version, "
                ":factor_name, :weight, TRUE "
                "FROM model_registry AS registry "
                "WHERE registry.is_active = TRUE "
                "AND registry.production_status = TRUE "
                "ON CONFLICT (sport, model_version, factor_name) "
                "DO NOTHING"
            ).bindparams(
                factor_name=factor_name,
                weight=weight,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABLE_NAME in inspector.get_table_names():
        op.drop_table(TABLE_NAME)
