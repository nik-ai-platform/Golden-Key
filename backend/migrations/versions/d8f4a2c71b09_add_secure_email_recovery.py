"""add secure email recovery

Revision ID: d8f4a2c71b09
Revises: c5a7e2d91f40
Create Date: 2026-08-31 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8f4a2c71b09"
down_revision: Union[str, None] = "c5a7e2d91f40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _challenge_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("recovery_email", sa.String(), nullable=False),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def _create_challenge_table(table_name: str) -> None:
    op.create_table(
        table_name,
        *_challenge_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f(f"ix_{table_name}_code_digest"),
        table_name,
        ["code_digest"],
        unique=True,
    )
    op.create_index(
        op.f(f"ix_{table_name}_user_id"),
        table_name,
        ["user_id"],
        unique=False,
    )


def upgrade() -> None:
    op.add_column("users", sa.Column("recovery_email", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "recovery_email_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_users_recovery_email"),
        "users",
        ["recovery_email"],
        unique=True,
    )
    _create_challenge_table("recovery_email_verifications")
    _create_challenge_table("forgot_email_challenges")


def downgrade() -> None:
    for table_name in ("forgot_email_challenges", "recovery_email_verifications"):
        op.drop_index(op.f(f"ix_{table_name}_user_id"), table_name=table_name)
        op.drop_index(op.f(f"ix_{table_name}_code_digest"), table_name=table_name)
        op.drop_table(table_name)
    op.drop_index(op.f("ix_users_recovery_email"), table_name="users")
    op.drop_column("users", "recovery_email_verified")
    op.drop_column("users", "recovery_email")
