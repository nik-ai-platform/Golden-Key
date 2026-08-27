"""merge performance heads

Revision ID: f1b7cb8a9a2e
Revises: 5f3e2d2d8b7a, d41b7f60c2aa
Create Date: 2026-08-04 23:20:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "f1b7cb8a9a2e"
down_revision: Union[str, Sequence[str], None] = ("5f3e2d2d8b7a", "d41b7f60c2aa")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass