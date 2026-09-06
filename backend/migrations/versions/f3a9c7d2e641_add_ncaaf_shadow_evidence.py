"""add ncaaf shadow evidence

Revision ID: f3a9c7d2e641
Revises: e7b4c2d91a60
Create Date: 2026-09-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a9c7d2e641"
down_revision: Union[str, None] = "e7b4c2d91a60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ncaaf_power_market_shadow_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("power_model_version", sa.String(), nullable=False),
        sa.Column("shadow_spec_version", sa.String(), nullable=False),
        sa.Column("generation_provenance", sa.String(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating_as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("neutral_site", sa.Boolean(), nullable=False),
        sa.Column("home_rating", sa.Float(), nullable=False),
        sa.Column("away_rating", sa.Float(), nullable=False),
        sa.Column("home_games_used", sa.Integer(), nullable=False),
        sa.Column("away_games_used", sa.Integer(), nullable=False),
        sa.Column("home_effective_games", sa.Float(), nullable=False),
        sa.Column("away_effective_games", sa.Float(), nullable=False),
        sa.Column("home_uncertainty", sa.Float(), nullable=False),
        sa.Column("away_uncertainty", sa.Float(), nullable=False),
        sa.Column("combined_uncertainty", sa.Float(), nullable=False),
        sa.Column("independent_model_margin", sa.Float(), nullable=False),
        sa.Column("odds_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("sportsbook", sa.String(), nullable=True),
        sa.Column("odds_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("spread_home", sa.Float(), nullable=False),
        sa.Column("spread_away", sa.Float(), nullable=True),
        sa.Column("market_margin", sa.Float(), nullable=False),
        sa.Column("disagreement", sa.Float(), nullable=False),
        sa.Column("abs_disagreement", sa.Float(), nullable=False),
        sa.Column("p_home_cover_shadow", sa.Float(), nullable=False),
        sa.Column("shadow_side", sa.String(), nullable=False),
        sa.Column("p_selected_shadow", sa.Float(), nullable=False),
        sa.Column("spread_price", sa.Integer(), nullable=False),
        sa.Column("price_source", sa.String(), nullable=False),
        sa.Column("break_even_probability", sa.Float(), nullable=False),
        sa.Column("shadow_edge", sa.Float(), nullable=False),
        sa.Column("evidence_gate_pass", sa.Boolean(), nullable=False),
        sa.Column("spread_safety_gate_pass", sa.Boolean(), nullable=False),
        sa.Column("power_input_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["odds_snapshot_id"], ["odds.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "power_model_version",
            "shadow_spec_version",
            name="uq_ncaaf_power_market_shadow_record",
        ),
    )
    op.create_index(
        "ix_ncaaf_shadow_record_game_id",
        "ncaaf_power_market_shadow_records",
        ["game_id"],
    )
    op.create_index(
        "ix_ncaaf_shadow_record_odds_snapshot_id",
        "ncaaf_power_market_shadow_records",
        ["odds_snapshot_id"],
    )
    op.create_index(
        "ix_ncaaf_shadow_record_power_input_hash",
        "ncaaf_power_market_shadow_records",
        ["power_input_hash"],
    )
    op.create_index(
        "ix_ncaaf_shadow_record_provenance_generated",
        "ncaaf_power_market_shadow_records",
        ["generation_provenance", "generated_at"],
    )

    op.create_table(
        "ncaaf_power_market_shadow_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shadow_record_id", sa.Integer(), nullable=False),
        sa.Column("home_score", sa.Float(), nullable=False),
        sa.Column("away_score", sa.Float(), nullable=False),
        sa.Column("actual_home_margin", sa.Float(), nullable=False),
        sa.Column("model_margin_error", sa.Float(), nullable=False),
        sa.Column("market_margin_error", sa.Float(), nullable=False),
        sa.Column("model_absolute_error", sa.Float(), nullable=False),
        sa.Column("market_absolute_error", sa.Float(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["shadow_record_id"],
            ["ncaaf_power_market_shadow_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shadow_record_id",
            name="uq_ncaaf_power_market_shadow_result",
        ),
    )


def downgrade() -> None:
    op.drop_table("ncaaf_power_market_shadow_results")
    op.drop_index(
        "ix_ncaaf_shadow_record_provenance_generated",
        table_name="ncaaf_power_market_shadow_records",
    )
    op.drop_index(
        "ix_ncaaf_shadow_record_power_input_hash",
        table_name="ncaaf_power_market_shadow_records",
    )
    op.drop_index(
        "ix_ncaaf_shadow_record_odds_snapshot_id",
        table_name="ncaaf_power_market_shadow_records",
    )
    op.drop_index(
        "ix_ncaaf_shadow_record_game_id",
        table_name="ncaaf_power_market_shadow_records",
    )
    op.drop_table("ncaaf_power_market_shadow_records")