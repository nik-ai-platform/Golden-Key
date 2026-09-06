"""add ncaaf history identity foundation

Revision ID: c2a8f4d91e63
Revises: a1e7c4d92b60
Create Date: 2026-09-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2a8f4d91e63"
down_revision: Union[str, None] = "a1e7c4d92b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GAME_COLUMNS = (
    ("neutral_site", sa.Boolean()),
    ("venue_name", sa.String()),
    ("venue_city", sa.String()),
    ("venue_state", sa.String()),
    ("historical_result_observed_at", sa.DateTime()),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "team_provider_identities" not in tables:
        op.create_table(
            "team_provider_identities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("sport", sa.String(), nullable=False),
            sa.Column("provider_team_id", sa.String(), nullable=False),
            sa.Column("provider_name", sa.String(), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "provider",
                "sport",
                "provider_team_id",
                name="uq_team_provider_identity",
            ),
        )
        op.create_index("ix_team_provider_identities_team_id", "team_provider_identities", ["team_id"])
        op.create_index(
            "ix_team_provider_identities_provider_sport",
            "team_provider_identities",
            ["provider", "sport"],
        )

    if "team_aliases" not in tables:
        op.create_table(
            "team_aliases",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=True),
            sa.Column("alias_name", sa.String(), nullable=False),
            sa.Column("normalized_alias", sa.String(), nullable=False),
            sa.Column("valid_from", sa.DateTime(), nullable=True),
            sa.Column("valid_to", sa.DateTime(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("review_state", sa.String(), server_default="unreviewed", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "team_id",
                "provider",
                "normalized_alias",
                name="uq_team_alias_provider_name",
            ),
        )
        op.create_index("ix_team_aliases_normalized_alias", "team_aliases", ["normalized_alias"])
        op.create_index("ix_team_aliases_team_id", "team_aliases", ["team_id"])

    if "team_seasons" not in tables:
        op.create_table(
            "team_seasons",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.Integer(), nullable=False),
            sa.Column("conference_name", sa.String(), nullable=True),
            sa.Column("classification", sa.String(), nullable=True),
            sa.Column("division", sa.String(), nullable=True),
            sa.Column("is_fbs", sa.Boolean(), nullable=True),
            sa.Column("source_provider", sa.String(), nullable=False),
            sa.Column("observed_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("team_id", "season", "source_provider", name="uq_team_season_source"),
        )

    if "game_provider_identities" not in tables:
        op.create_table(
            "game_provider_identities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("game_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("provider_game_id", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "provider_game_id", name="uq_game_provider_identity"),
        )
        op.create_index("ix_game_provider_identities_game_id", "game_provider_identities", ["game_id"])

    if "import_runs" not in tables:
        op.create_table(
            "import_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("import_type", sa.String(), nullable=False),
            sa.Column("season_start", sa.Integer(), nullable=True),
            sa.Column("season_end", sa.Integer(), nullable=True),
            sa.Column("dry_run", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("rows_fetched", sa.Integer(), server_default="0", nullable=False),
            sa.Column("teams_created", sa.Integer(), server_default="0", nullable=False),
            sa.Column("teams_matched", sa.Integer(), server_default="0", nullable=False),
            sa.Column("aliases_created", sa.Integer(), server_default="0", nullable=False),
            sa.Column("games_created", sa.Integer(), server_default="0", nullable=False),
            sa.Column("games_matched", sa.Integer(), server_default="0", nullable=False),
            sa.Column("games_updated", sa.Integer(), server_default="0", nullable=False),
            sa.Column("ambiguous_records", sa.Integer(), server_default="0", nullable=False),
            sa.Column("errors_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("checkpoint", sa.Text(), nullable=True),
            sa.Column("source_schema_version", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "game_result_observations" not in tables:
        op.create_table(
            "game_result_observations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("game_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("home_score", sa.Float(), nullable=True),
            sa.Column("away_score", sa.Float(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("observed_at", sa.DateTime(), nullable=False),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("payload_hash", sa.String(), nullable=True),
            sa.Column("import_run_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
            sa.ForeignKeyConstraint(["import_run_id"], ["import_runs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    game_columns = {column["name"] for column in inspector.get_columns("games")}
    for column_name, column_type in GAME_COLUMNS:
        if column_name not in game_columns:
            op.add_column("games", sa.Column(column_name, column_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "games" in tables:
        game_columns = {column["name"] for column in inspector.get_columns("games")}
        for column_name, _ in reversed(GAME_COLUMNS):
            if column_name in game_columns:
                op.drop_column("games", column_name)

    for table_name in (
        "game_result_observations",
        "import_runs",
        "game_provider_identities",
        "team_seasons",
        "team_aliases",
        "team_provider_identities",
    ):
        if table_name in tables:
            op.drop_table(table_name)