"""align subscriptions table

Revision ID: 87d7d9d66f10
Revises: 6af0a60f9f22
Create Date: 2026-08-05 23:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "87d7d9d66f10"
down_revision: Union[str, None] = "6af0a60f9f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "subscriptions" not in table_names:
        op.create_table(
            "subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("plan", sa.String(), nullable=True, server_default="free"),
            sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.true()),
            sa.Column("provider", sa.String(), nullable=True),
            sa.Column("provider_customer_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
        return

    columns = {column["name"] for column in inspector.get_columns("subscriptions")}
    indexes = {index["name"] for index in inspector.get_indexes("subscriptions")}

    if "active" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("active", sa.Boolean(), nullable=True, server_default=sa.true()),
        )
        if "status" in columns:
            op.execute(
                sa.text(
                    """
                    UPDATE subscriptions
                    SET active = CASE
                        WHEN upper(status) = 'ACTIVE' THEN TRUE
                        ELSE FALSE
                    END
                    """
                )
            )

    if "provider" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("provider", sa.String(), nullable=True),
        )
        if "billing_provider" in columns:
            op.execute(sa.text("UPDATE subscriptions SET provider = billing_provider WHERE provider IS NULL"))

    if "provider_customer_id" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("provider_customer_id", sa.String(), nullable=True),
        )

    if "updated_at" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if "plan" in columns:
        op.execute(sa.text("UPDATE subscriptions SET plan = lower(plan) WHERE plan IS NOT NULL"))

    if "billing_provider" in columns:
        op.drop_column("subscriptions", "billing_provider")

    if "status" in columns:
        op.drop_column("subscriptions", "status")

    if "renewal_date" in columns:
        op.drop_column("subscriptions", "renewal_date")

    if "ix_subscriptions_user_id" not in indexes:
        op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "subscriptions" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("subscriptions")}

    if "billing_provider" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("billing_provider", sa.String(length=64), nullable=True),
        )
        if "provider" in columns:
            op.execute(sa.text("UPDATE subscriptions SET billing_provider = provider WHERE provider IS NOT NULL"))

    if "status" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("status", sa.String(length=32), nullable=True, server_default="ACTIVE"),
        )
        if "active" in columns:
            op.execute(
                sa.text(
                    """
                    UPDATE subscriptions
                    SET status = CASE
                        WHEN active IS FALSE THEN 'INACTIVE'
                        ELSE 'ACTIVE'
                    END
                    """
                )
            )

    if "renewal_date" not in columns:
        op.add_column(
            "subscriptions",
            sa.Column("renewal_date", sa.DateTime(), nullable=True),
        )

    if "plan" in columns:
        op.execute(sa.text("UPDATE subscriptions SET plan = upper(plan) WHERE plan IS NOT NULL"))

    columns = {column["name"] for column in inspector.get_columns("subscriptions")}

    if "provider_customer_id" in columns:
        op.drop_column("subscriptions", "provider_customer_id")

    if "provider" in columns:
        op.drop_column("subscriptions", "provider")

    if "updated_at" in columns:
        op.drop_column("subscriptions", "updated_at")

    if "active" in columns:
        op.drop_column("subscriptions", "active")