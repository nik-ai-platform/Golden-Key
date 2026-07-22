"""add provider game id

Revision ID: 39b705f4d87c
Revises: 
Create Date: 2026-07-21 20:02:57.371249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '39b705f4d87c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'games',
        sa.Column(
            'provider_game_id',
            sa.String(),
            nullable=True
        )
    )

    op.create_index(
        op.f('ix_games_provider_game_id'),
        'games',
        ['provider_game_id'],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_games_provider_game_id'), table_name='games')
    op.drop_column('games', 'provider_game_id')
