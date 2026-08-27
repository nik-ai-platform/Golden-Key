"""add unique constraint user predictions

Revision ID: 6af0a60f9f22
Revises: e6d14b9dcb31
Create Date: 2026-08-05 22:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6af0a60f9f22"
down_revision: Union[str, None] = "e6d14b9dcb31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_constraints = {
        c["name"] for c in inspector.get_unique_constraints("user_predictions") if c.get("name")
    }

    # Keep the lowest id row for each duplicate user/prediction pair before adding uniqueness.
    op.execute(
        sa.text(
            """
            DELETE FROM user_predictions up
            USING user_predictions dup
            WHERE up.id > dup.id
              AND up.user_id = dup.user_id
              AND up.prediction_id = dup.prediction_id
            """
        )
    )

    if "uq_user_predictions_user_prediction" not in existing_constraints:
        op.create_unique_constraint(
            "uq_user_predictions_user_prediction",
            "user_predictions",
            ["user_id", "prediction_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_constraints = {
        c["name"] for c in inspector.get_unique_constraints("user_predictions") if c.get("name")
    }

    if "uq_user_predictions_user_prediction" in existing_constraints:
        op.drop_constraint(
            "uq_user_predictions_user_prediction",
            "user_predictions",
            type_="unique",
        )