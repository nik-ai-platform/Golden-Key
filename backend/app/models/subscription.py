from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey
)
from enum import Enum

from sqlalchemy.sql import func

from app.database.base import Base


class SubscriptionPlan(str, Enum):

    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ELITE = "ELITE"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(str, Enum):

    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"
    TRIALING = "TRIALING"


class Subscription(Base):

    __tablename__ = "subscriptions"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id"
        ),
        nullable=False
    )

    plan = Column(
        String,
        default="free"
    )

    active = Column(
        Boolean,
        default=True
    )

    provider = Column(
        String,
        nullable=True
    )

    provider_customer_id = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        onupdate=func.now()
    )

    @property
    def status(self) -> str:
        return (
            SubscriptionStatus.ACTIVE.value
            if self.active
            else SubscriptionStatus.CANCELED.value
        )

    @status.setter
    def status(self, value: str) -> None:
        self.active = value in {
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.TRIALING.value,
        }
