"""Capture observed paired prices without inventing historical values."""

import sqlalchemy as sa
from alembic import op

revision = "b0c3f5e8d142"
down_revision = "a9b2e4d7c031"
branch_labels = None
depends_on = None

PRICE_COLUMNS = (
    "spread_home_price", "spread_away_price", "total_over_price", "total_under_price",
)


def upgrade() -> None:
    for name in PRICE_COLUMNS:
        op.add_column("odds", sa.Column(name, sa.Integer(), nullable=True))


def downgrade() -> None:
    for name in reversed(PRICE_COLUMNS):
        op.drop_column("odds", name)
