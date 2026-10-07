"""Record verified provider chronology without rewriting legacy events."""

from alembic import op
import sqlalchemy as sa

revision = "a9b2e4d7c031"
down_revision = "f8a1d3c6b920"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_subscription_events",
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_provider_event_subscription_chronology",
        "provider_subscription_events",
        ["provider", "external_subscription_id", "processing_status", "provider_created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_event_subscription_chronology",
        table_name="provider_subscription_events",
    )
    op.drop_column("provider_subscription_events", "provider_created_at")
