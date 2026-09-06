"""add ncaaf power rating persistence

Revision ID: e7b4c2d91a60
Revises: c2a8f4d91e63
Create Date: 2026-09-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7b4c2d91a60"
down_revision: Union[str, None] = "c2a8f4d91e63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "team_power_rating_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport", sa.String(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("uncertainty", sa.Float(), nullable=False),
        sa.Column("games_used", sa.Integer(), nullable=False),
        sa.Column("effective_games", sa.Float(), nullable=False),
        sa.Column("rating_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_max_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_game_count", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "model_version",
            "rating_as_of",
            name="uq_team_power_rating_snapshot",
        ),
    )
    op.create_index(
        "ix_team_power_rating_input_hash",
        "team_power_rating_records",
        ["input_hash"],
    )
    op.create_index(
        "ix_team_power_rating_season_as_of",
        "team_power_rating_records",
        ["sport", "season", "rating_as_of"],
    )
    op.create_index(
        "ix_team_power_rating_team_id",
        "team_power_rating_records",
        ["team_id"],
    )

    op.create_table(
        "prediction_power_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("rating_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("home_rating", sa.Float(), nullable=False),
        sa.Column("away_rating", sa.Float(), nullable=False),
        sa.Column("home_uncertainty", sa.Float(), nullable=False),
        sa.Column("away_uncertainty", sa.Float(), nullable=False),
        sa.Column("home_games_used", sa.Integer(), nullable=False),
        sa.Column("away_games_used", sa.Integer(), nullable=False),
        sa.Column("home_effective_games", sa.Float(), nullable=False),
        sa.Column("away_effective_games", sa.Float(), nullable=False),
        sa.Column("minimum_games_used", sa.Integer(), nullable=False),
        sa.Column("combined_uncertainty", sa.Float(), nullable=False),
        sa.Column("neutral_site", sa.Boolean(), nullable=False),
        sa.Column("home_field_points", sa.Float(), nullable=False),
        sa.Column("independent_model_margin", sa.Float(), nullable=False),
        sa.Column("source_max_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_game_count", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "model_version",
            "rating_as_of",
            name="uq_prediction_power_snapshot",
        ),
    )
    op.create_index(
        "ix_prediction_power_snapshot_game_id",
        "prediction_power_snapshots",
        ["game_id"],
    )
    op.create_index(
        "ix_prediction_power_snapshot_input_hash",
        "prediction_power_snapshots",
        ["input_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prediction_power_snapshot_input_hash",
        table_name="prediction_power_snapshots",
    )
    op.drop_index(
        "ix_prediction_power_snapshot_game_id",
        table_name="prediction_power_snapshots",
    )
    op.drop_table("prediction_power_snapshots")
    op.drop_index(
        "ix_team_power_rating_team_id",
        table_name="team_power_rating_records",
    )
    op.drop_index(
        "ix_team_power_rating_season_as_of",
        table_name="team_power_rating_records",
    )
    op.drop_index(
        "ix_team_power_rating_input_hash",
        table_name="team_power_rating_records",
    )
    op.drop_table("team_power_rating_records")