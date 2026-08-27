"""expand backtest results schema

Revision ID: c7b2e4d1a9f0
Revises: 9a8c3d6e4f21
Create Date: 2026-08-05 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7b2e4d1a9f0"
down_revision: Union[str, Sequence[str], None] = "9a8c3d6e4f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("backtest_results")}

    def add_column_if_missing(column_name: str, column: sa.Column) -> None:
        if column_name not in columns:
            op.add_column("backtest_results", column)

    add_column_if_missing("sport", sa.Column("sport", sa.String(), nullable=True))
    add_column_if_missing("start_date", sa.Column("start_date", sa.Date(), nullable=True))
    add_column_if_missing("end_date", sa.Column("end_date", sa.Date(), nullable=True))
    add_column_if_missing("games_tested", sa.Column("games_tested", sa.Integer(), nullable=True))
    add_column_if_missing("ats_record", sa.Column("ats_record", sa.String(), nullable=True))
    add_column_if_missing("roi", sa.Column("roi", sa.Float(), nullable=True))
    add_column_if_missing("calibration_error", sa.Column("calibration_error", sa.Float(), nullable=True))
    add_column_if_missing(
        "created_at",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_column("backtest_results", "created_at")
    op.drop_column("backtest_results", "calibration_error")
    op.drop_column("backtest_results", "roi")
    op.drop_column("backtest_results", "ats_record")
    op.drop_column("backtest_results", "games_tested")
    op.drop_column("backtest_results", "end_date")
    op.drop_column("backtest_results", "start_date")
    op.drop_column("backtest_results", "sport")