"""add prediction integrity fields

Revision ID: f4a9c2e71d30
Revises: d8f4a2c71b09
Create Date: 2026-08-31 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a9c2e71d30"
down_revision: Union[str, None] = "d8f4a2c71b09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("odds_snapshot_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("sportsbook", sa.String(), nullable=True),
    )
    op.add_column(
        "predictions",
        sa.Column("odds_observed_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_predictions_odds_snapshot_id",
        "predictions",
        "odds",
        ["odds_snapshot_id"],
        ["id"],
    )
    op.create_index(
        "ix_predictions_odds_snapshot_id",
        "predictions",
        ["odds_snapshot_id"],
        unique=False,
    )

    op.add_column(
        "games",
        sa.Column(
            "status",
            sa.String(),
            server_default="scheduled",
            nullable=False,
        ),
    )
    op.add_column(
        "games",
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        "UPDATE games SET status = 'final', completed_at = game_date "
        "WHERE home_score IS NOT NULL AND away_score IS NOT NULL"
    )
    op.create_index(
        "ix_games_status_game_date",
        "games",
        ["status", "game_date"],
        unique=False,
    )

    op.create_table(
        "prediction_line_corrections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("original_line", sa.Float(), nullable=True),
        sa.Column("corrected_line", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prediction_line_corrections_prediction_id",
        "prediction_line_corrections",
        ["prediction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prediction_line_corrections_prediction_id",
        table_name="prediction_line_corrections",
    )
    op.drop_table("prediction_line_corrections")
    op.drop_index("ix_games_status_game_date", table_name="games")
    op.drop_column("games", "completed_at")
    op.drop_column("games", "status")
    op.drop_index("ix_predictions_odds_snapshot_id", table_name="predictions")
    op.drop_constraint(
        "fk_predictions_odds_snapshot_id",
        "predictions",
        type_="foreignkey",
    )
    op.drop_column("predictions", "odds_observed_at")
    op.drop_column("predictions", "sportsbook")
    op.drop_column("predictions", "odds_snapshot_id")