"""add weight profiles table

Revision ID: 9a8c3d6e4f21
Revises: f1b7cb8a9a2e
Create Date: 2026-08-05 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a8c3d6e4f21"
down_revision: Union[str, Sequence[str], None] = "f1b7cb8a9a2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weight_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sport", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("profile_name", sa.String(), nullable=False),
        sa.Column("weights_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_index("ix_weight_profiles_sport", "weight_profiles", ["sport"], unique=False)
    op.create_index("ix_weight_profiles_model_version", "weight_profiles", ["model_version"], unique=False)
    op.create_index(
        "ix_weight_profiles_sport_version_active",
        "weight_profiles",
        ["sport", "model_version", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_weight_profiles_sport_version_active", table_name="weight_profiles")
    op.drop_index("ix_weight_profiles_model_version", table_name="weight_profiles")
    op.drop_index("ix_weight_profiles_sport", table_name="weight_profiles")
    op.drop_table("weight_profiles")
