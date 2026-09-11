"""add ncaaf rule intelligence

Revision ID: b8d4e6f2a731
Revises: a4c8e2f19b73
Create Date: 2026-09-11 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d4e6f2a731"
down_revision: Union[str, None] = "a4c8e2f19b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ncaaf_rule_intelligence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("odds_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("rule_team_location", sa.String(), nullable=False),
        sa.Column("rule_spread", sa.Float(), nullable=False),
        sa.Column("rule_semantics", sa.String(), nullable=False),
        sa.Column("rule_pick_side", sa.String(), nullable=False),
        sa.Column("rule_pick_line", sa.Float(), nullable=False),
        sa.Column("npi_selection", sa.String(), nullable=False),
        sa.Column("comparison", sa.String(), nullable=False),
        sa.Column("rule_result", sa.String(), nullable=True),
        sa.Column("npi_result", sa.String(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rule_team_location IN ('HOME', 'AWAY')",
            name="ck_ncaaf_rule_intelligence_team_location",
        ),
        sa.CheckConstraint(
            "rule_semantics IN ('COVERS', 'DOES_NOT_COVER')",
            name="ck_ncaaf_rule_intelligence_semantics",
        ),
        sa.CheckConstraint(
            "rule_pick_side IN ('HOME', 'AWAY')",
            name="ck_ncaaf_rule_intelligence_pick_side",
        ),
        sa.CheckConstraint(
            "npi_selection IN ('HOME', 'AWAY', 'PASS')",
            name="ck_ncaaf_rule_intelligence_npi_selection",
        ),
        sa.CheckConstraint(
            "comparison IN ('AGREE', 'DISAGREE', 'NPI_PASS')",
            name="ck_ncaaf_rule_intelligence_comparison",
        ),
        sa.CheckConstraint(
            "rule_result IS NULL OR rule_result IN ('WIN', 'LOSS', 'PUSH')",
            name="ck_ncaaf_rule_intelligence_rule_result",
        ),
        sa.CheckConstraint(
            "npi_result IS NULL OR npi_result IN ('WIN', 'LOSS', 'PUSH')",
            name="ck_ncaaf_rule_intelligence_npi_result",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["odds_snapshot_id"], ["odds.id"]),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_prediction_id",
        "ncaaf_rule_intelligence",
        ["prediction_id"],
        unique=True,
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_game_id",
        "ncaaf_rule_intelligence",
        ["game_id"],
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_odds_snapshot_id",
        "ncaaf_rule_intelligence",
        ["odds_snapshot_id"],
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_rule_code",
        "ncaaf_rule_intelligence",
        ["rule_code"],
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_comparison",
        "ncaaf_rule_intelligence",
        ["comparison"],
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_settled_at",
        "ncaaf_rule_intelligence",
        ["settled_at"],
    )
    op.create_index(
        "ix_ncaaf_rule_intelligence_rule_comparison",
        "ncaaf_rule_intelligence",
        ["rule_code", "comparison"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ncaaf_rule_intelligence_rule_comparison",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_index(
        "ix_ncaaf_rule_intelligence_settled_at",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_index(
        "ix_ncaaf_rule_intelligence_comparison",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_index(
        "ix_ncaaf_rule_intelligence_rule_code",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_index(
        "ix_ncaaf_rule_intelligence_odds_snapshot_id",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_index(
        "ix_ncaaf_rule_intelligence_game_id",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_index(
        "ix_ncaaf_rule_intelligence_prediction_id",
        table_name="ncaaf_rule_intelligence",
    )
    op.drop_table("ncaaf_rule_intelligence")