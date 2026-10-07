"""Persist authentication state without importing process-local credentials.

Revision ID: f8a1d3c6b920
Revises: e7b4c2d9a610

New tables intentionally start empty: all old in-memory refresh sessions and
verification links become invalid. No unsafe session backfill is possible.
Downgrade drops authentication state and requires every customer to sign in again.
"""

from alembic import op
import sqlalchemy as sa

revision = "f8a1d3c6b920"
down_revision = "e7b4c2d9a610"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_access_sessions",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_auth_access_sessions_user_id", "auth_access_sessions", ["user_id"])
    op.create_table(
        "auth_verified_emails",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("verified_at", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "auth_refresh_sessions",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "auth_revoked_tokens",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "auth_login_failures",
        sa.Column("subject_digest", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "auth_email_verification_tokens",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("issued_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    for table in (
        "auth_access_sessions", "auth_refresh_sessions", "auth_revoked_tokens",
        "auth_login_failures", "auth_email_verification_tokens",
    ):
        op.create_index(f"ix_{table}_expires_at", table, ["expires_at"])
    op.create_index(
        "ix_auth_email_verification_tokens_user_id",
        "auth_email_verification_tokens", ["user_id"],
    )


def downgrade() -> None:
    for table in (
        "auth_email_verification_tokens", "auth_login_failures",
        "auth_revoked_tokens", "auth_refresh_sessions", "auth_access_sessions",
    ):
        op.drop_table(table)
    op.drop_table("auth_verified_emails")
