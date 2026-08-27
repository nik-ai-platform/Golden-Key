"""add backtest per game fields

Revision ID: a8b1f6d3e4c2
Revises: 9d12b4ac7f31
Create Date: 2026-08-07 12:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b1f6d3e4c2"
down_revision: Union[str, None] = "9d12b4ac7f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "backtest_results" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("backtest_results")}

    def add_column_if_missing(name: str, column: sa.Column) -> None:
        if name not in columns:
            op.add_column("backtest_results", column)
            columns.add(name)

    add_column_if_missing("backtest_id", sa.Column("backtest_id", sa.Integer(), nullable=True))
    add_column_if_missing("game_id", sa.Column("game_id", sa.Integer(), nullable=True))
    add_column_if_missing("predicted_side", sa.Column("predicted_side", sa.String(), nullable=True))
    add_column_if_missing("actual_side", sa.Column("actual_side", sa.String(), nullable=True))
    add_column_if_missing("spread", sa.Column("spread", sa.Float(), nullable=True))
    add_column_if_missing("npi_score", sa.Column("npi_score", sa.Float(), nullable=True))
    add_column_if_missing("confidence", sa.Column("confidence", sa.Float(), nullable=True))
    add_column_if_missing("win_loss", sa.Column("win_loss", sa.String(), nullable=True))
    add_column_if_missing("profit_loss", sa.Column("profit_loss", sa.Float(), nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("backtest_results")}
    if "ix_backtest_results_backtest_id" not in indexes:
        op.create_index(
            "ix_backtest_results_backtest_id",
            "backtest_results",
            ["backtest_id"],
            unique=False,
        )

    foreign_keys = inspector.get_foreign_keys("backtest_results")
    has_game_fk = any(
        fk.get("referred_table") == "games" and fk.get("constrained_columns") == ["game_id"]
        for fk in foreign_keys
    )
    if "game_id" in columns and not has_game_fk:
        op.create_foreign_key(
            "fk_backtest_results_game_id_games",
            "backtest_results",
            "games",
            ["game_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "backtest_results" not in inspector.get_table_names():
        return

    foreign_keys = inspector.get_foreign_keys("backtest_results")
    for fk in foreign_keys:
        if fk.get("name") == "fk_backtest_results_game_id_games":
            op.drop_constraint("fk_backtest_results_game_id_games", "backtest_results", type_="foreignkey")
            break

    indexes = {index["name"] for index in inspector.get_indexes("backtest_results")}
    if "ix_backtest_results_backtest_id" in indexes:
        op.drop_index("ix_backtest_results_backtest_id", table_name="backtest_results")

    columns = {column["name"] for column in inspector.get_columns("backtest_results")}
    for name in [
        "profit_loss",
        "win_loss",
        "confidence",
        "npi_score",
        "spread",
        "actual_side",
        "predicted_side",
        "game_id",
        "backtest_id",
    ]:
        if name in columns:
            op.drop_column("backtest_results", name)
