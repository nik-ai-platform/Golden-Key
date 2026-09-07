from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class EntitlementStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"


class ApplicationEntitlement(Base):
    __tablename__ = "application_entitlements"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "entitlement_key",
            name="uq_application_entitlement_user_key",
        ),
        Index("ix_application_entitlements_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    entitlement_key = Column(String, nullable=False)
    plan = Column(String, nullable=False)
    status = Column(String, nullable=False)
    source_provider = Column(String, nullable=True)
    source_subscription_id = Column(
        Integer,
        ForeignKey("provider_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=True)
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

    user = relationship("User", back_populates="application_entitlements")
    source_subscription = relationship(
        "ProviderSubscription",
        back_populates="application_entitlements",
    )