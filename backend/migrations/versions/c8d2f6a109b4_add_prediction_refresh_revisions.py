"""Allow immutable prediction refresh revisions.

Revision ID: c8d2f6a109b4
Revises: c6f2a8d4e913, a4c8e2f19b73
"""

from alembic import op
import sqlalchemy as sa


revision = "c8d2f6a109b4"
down_revision = ("c6f2a8d4e913", "a4c8e2f19b73")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("generation_id", sa.String(36), nullable=True))
    op.add_column("predictions", sa.Column("input_fingerprint", sa.String(64), nullable=True))
    op.execute(sa.text(
        "UPDATE predictions SET generation_id = "
        "substr(md5('legacy-prediction:' || CAST(id AS TEXT)), 1, 8) || '-' || "
        "substr(md5('legacy-prediction:' || CAST(id AS TEXT)), 9, 4) || '-' || "
        "substr(md5('legacy-prediction:' || CAST(id AS TEXT)), 13, 4) || '-' || "
        "substr(md5('legacy-prediction:' || CAST(id AS TEXT)), 17, 4) || '-' || "
        "substr(md5('legacy-prediction:' || CAST(id AS TEXT)), 21, 12), "
        "input_fingerprint = 'unverified:legacy'"
    ))
    op.alter_column("predictions", "generation_id", existing_type=sa.String(36), nullable=False)
    op.alter_column("predictions", "input_fingerprint", existing_type=sa.String(64), nullable=False)
    op.create_check_constraint(
        "ck_predictions_generation_id", "predictions", "length(generation_id) = 36",
    )
    op.create_check_constraint(
        "ck_predictions_input_fingerprint", "predictions",
        "length(input_fingerprint) = 64 OR input_fingerprint IN "
        "('unverified:legacy', 'unverified:manual')",
    )
    op.drop_index("ix_predictions_game_model_market", table_name="predictions")
    op.create_index(
        "ix_predictions_game_model_market",
        "predictions",
        ["game_id", "model_version", "market", "generation_id"],
        unique=True,
    )


def downgrade() -> None:
    # Refuse a lossy downgrade once multiple publications exist for a market.
    duplicates = op.get_bind().execute(sa.text(
        "SELECT 1 FROM predictions WHERE model_version IS NOT NULL "
        "GROUP BY game_id, model_version, market "
        "HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates is not None:
        raise RuntimeError("Cannot downgrade immutable prediction revisions without losing history")
    op.drop_index("ix_predictions_game_model_market", table_name="predictions")
    op.create_index(
        "ix_predictions_game_model_market", "predictions",
        ["game_id", "model_version", "market"], unique=True,
    )
    op.drop_constraint("ck_predictions_input_fingerprint", "predictions", type_="check")
    op.drop_constraint("ck_predictions_generation_id", "predictions", type_="check")
    op.drop_column("predictions", "input_fingerprint")
    op.drop_column("predictions", "generation_id")
