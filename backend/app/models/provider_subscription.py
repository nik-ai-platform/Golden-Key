from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class SubscriptionProvider(str, Enum):
    STRIPE = "stripe"
    APPLE = "apple"
    ADMIN = "admin"


class ProviderSubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ProviderSubscription(Base):
    __tablename__ = "provider_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_subscription_id",
            name="uq_provider_subscription_identity",
        ),
        Index("ix_provider_subscriptions_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String, nullable=False)
    external_customer_id = Column(String, nullable=True)
    external_subscription_id = Column(String, nullable=True)
    external_product_id = Column(String, nullable=True)
    plan = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="provider_subscriptions")
    application_entitlements = relationship(
        "ApplicationEntitlement",
        back_populates="source_subscription",
    )