"""add model promotion fields

Revision ID: b7e3a91c5d42
Revises: a8b1f6d3e4c2
Create Date: 2026-08-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e3a91c5d42"
down_revision: Union[str, None] = "a8b1f6d3e4c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "model_versions" in table_names:
        columns = _column_names(inspector, "model_versions")

        if "sport" not in columns:
            op.add_column(
                "model_versions",
                sa.Column("sport", sa.String(length=64), nullable=True),
            )
        if "games_evaluated" not in columns:
            op.add_column(
                "model_versions",
                sa.Column(
                    "games_evaluated",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )

        op.execute(
            sa.text(
                "UPDATE model_versions "
                "SET sport = 'unknown' "
                "WHERE sport IS NULL OR sport = ''"
            )
        )
        op.alter_column(
            "model_versions",
            "sport",
            existing_type=sa.String(length=64),
            nullable=False,
        )

        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "model_versions")
        if "ix_model_versions_version" not in indexes:
            op.create_index(
                "ix_model_versions_version",
                "model_versions",
                ["version"],
                unique=False,
            )
        if "ix_model_versions_sport" not in indexes:
            op.create_index(
                "ix_model_versions_sport",
                "model_versions",
                ["sport"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "model_registry" not in table_names:
        op.create_table(
            "model_registry",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("model_name", sa.String(length=150), nullable=False),
            sa.Column("model_version", sa.String(length=50), nullable=False),
            sa.Column("sport", sa.String(length=50), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=False),
            sa.Column("training_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("validation_score", sa.Float(), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "production_status",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_model_registry_id", "model_registry", ["id"], unique=False)
        op.create_index(
            "ix_model_registry_model_version",
            "model_registry",
            ["model_version"],
            unique=False,
        )
        op.create_index(
            "ix_model_registry_sport",
            "model_registry",
            ["sport"],
            unique=False,
        )
    else:
        columns = _column_names(inspector, "model_registry")

        if "model_version" not in columns:
            op.add_column(
                "model_registry",
                sa.Column("model_version", sa.String(length=50), nullable=True),
            )
        if "is_active" not in columns:
            op.add_column(
                "model_registry",
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )

        columns = _column_names(sa.inspect(bind), "model_registry")
        version_source = "version" if "version" in columns else "'unknown'"
        active_source = (
            "production_status"
            if "production_status" in columns
            else "false"
        )
        op.execute(
            sa.text(
                "UPDATE model_registry "
                f"SET model_version = COALESCE(model_version, {version_source}, 'unknown'), "
                f"is_active = COALESCE(is_active, {active_source}, false)"
            )
        )
        op.alter_column(
            "model_registry",
            "model_version",
            existing_type=sa.String(length=50),
            nullable=False,
        )
        if "sport" in columns:
            op.execute(
                sa.text(
                    "UPDATE model_registry "
                    "SET sport = 'unknown' "
                    "WHERE sport IS NULL OR sport = ''"
                )
            )
            op.alter_column(
                "model_registry",
                "sport",
                existing_type=sa.String(length=50),
                nullable=False,
            )

        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "model_registry")
        if "ix_model_registry_model_version" not in indexes:
            op.create_index(
                "ix_model_registry_model_version",
                "model_registry",
                ["model_version"],
                unique=False,
            )
        if "sport" in columns and "ix_model_registry_sport" not in indexes:
            op.create_index(
                "ix_model_registry_sport",
                "model_registry",
                ["sport"],
                unique=False,
            )

    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "backtest_results" in table_names:
        columns = _column_names(inspector, "backtest_results")

        if "market" not in columns:
            op.add_column(
                "backtest_results",
                sa.Column("market", sa.String(), nullable=True),
            )
        if "outcome" not in columns:
            op.add_column(
                "backtest_results",
                sa.Column("outcome", sa.String(), nullable=True),
            )

        columns = _column_names(sa.inspect(bind), "backtest_results")
        outcome_source = "win_loss" if "win_loss" in columns else "'PUSH'"
        op.execute(
            sa.text(
                "UPDATE backtest_results "
                "SET model_version = COALESCE(model_version, 'unknown'), "
                "sport = COALESCE(sport, 'unknown'), "
                "market = COALESCE(market, 'spread'), "
                f"outcome = COALESCE(outcome, {outcome_source}, 'PUSH')"
            )
        )
        op.alter_column(
            "backtest_results",
            "model_version",
            existing_type=sa.String(),
            nullable=False,
        )
        op.alter_column(
            "backtest_results",
            "sport",
            existing_type=sa.String(),
            nullable=False,
        )
        op.alter_column(
            "backtest_results",
            "market",
            existing_type=sa.String(),
            nullable=False,
        )
        op.alter_column(
            "backtest_results",
            "outcome",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "backtest_results" in table_names:
        columns = _column_names(inspector, "backtest_results")
        if "outcome" in columns:
            op.drop_column("backtest_results", "outcome")
        if "market" in columns:
            op.drop_column("backtest_results", "market")
        if "sport" in columns:
            op.alter_column(
                "backtest_results",
                "sport",
                existing_type=sa.String(),
                nullable=True,
            )
        if "model_version" in columns:
            op.alter_column(
                "backtest_results",
                "model_version",
                existing_type=sa.String(),
                nullable=True,
            )

    inspector = sa.inspect(bind)
    if "model_registry" in inspector.get_table_names():
        op.drop_table("model_registry")

    inspector = sa.inspect(bind)
    if "model_versions" in inspector.get_table_names():
        indexes = _index_names(inspector, "model_versions")
        if "ix_model_versions_sport" in indexes:
            op.drop_index("ix_model_versions_sport", table_name="model_versions")
        if "ix_model_versions_version" in indexes:
            op.drop_index("ix_model_versions_version", table_name="model_versions")

        columns = _column_names(sa.inspect(bind), "model_versions")
        if "games_evaluated" in columns:
            op.drop_column("model_versions", "games_evaluated")
        if "sport" in columns:
            op.drop_column("model_versions", "sport")
