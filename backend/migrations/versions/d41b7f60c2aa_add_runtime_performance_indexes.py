"""add runtime performance indexes

Revision ID: d41b7f60c2aa
Revises: 0249a31c1dbc
Create Date: 2026-08-04 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d41b7f60c2aa"
down_revision: Union[str, Sequence[str], None] = "0249a31c1dbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    game_columns = {column["name"] for column in inspector.get_columns("games")}
    score_columns = {column["name"] for column in inspector.get_columns("nik_scores")}
    performance_columns = {column["name"] for column in inspector.get_columns("team_performance")}

    if "created_at" not in score_columns:
        op.add_column(
            "nik_scores",
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )

    def create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
        existing = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name not in existing:
            op.create_index(index_name, table_name, columns, unique=False)

    if "game_date" in game_columns:
        create_index_if_missing("ix_games_game_date", "games", ["game_date"])

    if "game_id" in score_columns:
        create_index_if_missing("ix_nik_scores_game_id", "nik_scores", ["game_id"])

    create_index_if_missing("ix_nik_scores_created_at", "nik_scores", ["created_at"])

    if "team_id" in performance_columns:
        create_index_if_missing("ix_team_performance_team_id", "team_performance", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_team_performance_team_id", table_name="team_performance")
    op.drop_index("ix_nik_scores_created_at", table_name="nik_scores")
    op.drop_index("ix_nik_scores_game_id", table_name="nik_scores")
    op.drop_index("ix_games_game_date", table_name="games")
    op.drop_column("nik_scores", "created_at")