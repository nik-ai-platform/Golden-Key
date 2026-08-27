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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'teams' not in tables:
        op.create_table(
            'teams',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('league', sa.String(), nullable=False),
            sa.Column('sport', sa.String(), nullable=False),
            sa.Column('power_rating', sa.Float(), nullable=True),
        )
        op.create_index('ix_teams_id', 'teams', ['id'], unique=False)

    if 'games' not in tables:
        op.create_table(
            'games',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('sport', sa.String(), nullable=False),
            sa.Column('league', sa.String(), nullable=False),
            sa.Column('season', sa.Integer(), nullable=True),
            sa.Column('home_team_id', sa.Integer(), nullable=False),
            sa.Column('away_team_id', sa.Integer(), nullable=False),
            sa.Column('game_date', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['home_team_id'], ['teams.id']),
            sa.ForeignKeyConstraint(['away_team_id'], ['teams.id']),
        )
        op.create_index('idx_game_sport_date', 'games', ['sport', 'game_date'], unique=False)
        op.create_index('idx_game_teams', 'games', ['home_team_id', 'away_team_id'], unique=False)

    if 'odds' not in tables:
        op.create_table(
            'odds',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('game_id', sa.Integer(), nullable=True),
            sa.Column('sportsbook', sa.String(), nullable=True),
            sa.Column('spread_home', sa.Float(), nullable=True),
            sa.Column('spread_away', sa.Float(), nullable=True),
            sa.Column('moneyline_home', sa.Integer(), nullable=True),
            sa.Column('moneyline_away', sa.Integer(), nullable=True),
            sa.Column('total', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['game_id'], ['games.id']),
        )

    if 'nik_scores' not in tables:
        op.create_table(
            'nik_scores',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('game_id', sa.Integer(), nullable=True),
            sa.Column('ats_score', sa.Float(), nullable=True),
            sa.Column('ml_score', sa.Float(), nullable=True),
            sa.Column('total_score', sa.Float(), nullable=True),
            sa.Column('final_npi', sa.Float(), nullable=True),
            sa.Column('recommendation', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['game_id'], ['games.id']),
        )

    if 'injuries' not in tables:
        op.create_table(
            'injuries',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('team', sa.String(), nullable=True),
            sa.Column('player', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=True),
            sa.Column('impact', sa.Float(), nullable=True),
        )

    inspector = sa.inspect(bind)
    game_columns = {column['name'] for column in inspector.get_columns('games')}
    if 'provider_game_id' not in game_columns:
        op.add_column('games', sa.Column('provider_game_id', sa.String(), nullable=True))

    game_indexes = {index['name'] for index in inspector.get_indexes('games')}
    if op.f('ix_games_provider_game_id') not in game_indexes:
        op.create_index(op.f('ix_games_provider_game_id'), 'games', ['provider_game_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_games_provider_game_id'), table_name='games')
    op.drop_column('games', 'provider_game_id')
