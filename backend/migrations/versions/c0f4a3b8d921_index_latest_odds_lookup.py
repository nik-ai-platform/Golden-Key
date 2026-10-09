"""index the latest odds snapshot lookup

Revision ID: c0f4a3b8d921
Revises: b0c3f5e8d142
Create Date: 2026-08-05 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c0f4a3b8d921"
down_revision: str | Sequence[str] | None = "b0c3f5e8d142"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEX_NAME = "ix_odds_game_book_created_id"


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.create_index(
                INDEX_NAME,
                "odds",
                ["game_id", "sportsbook", "created_at", "id"],
                unique=False,
                postgresql_concurrently=True,
            )
        return

    op.create_index(
        INDEX_NAME,
        "odds",
        ["game_id", "sportsbook", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.drop_index(
                INDEX_NAME,
                table_name="odds",
                postgresql_concurrently=True,
            )
        return

    op.drop_index(INDEX_NAME, table_name="odds")
