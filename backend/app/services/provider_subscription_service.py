from datetime import datetime

from sqlalchemy.orm import Session

from app.models.provider_subscription import (
    ProviderSubscription,
    ProviderSubscriptionStatus,
    SubscriptionProvider,
)


def get_by_provider_subscription_id(
    db: Session,
    provider: str,
    external_subscription_id: str,
) -> ProviderSubscription | None:
    return (
        db.query(ProviderSubscription)
        .filter(
            ProviderSubscription.provider == provider,
            ProviderSubscription.external_subscription_id == external_subscription_id,
        )
        .one_or_none()
    )


def create_or_update_provider_subscription(
    db: Session,
    *,
    user_id: int,
    provider: str,
    plan: str,
    status: str,
    external_customer_id: str | None = None,
    external_subscription_id: str | None = None,
    external_product_id: str | None = None,
    current_period_start: datetime | None = None,
    current_period_end: datetime | None = None,
    trial_end: datetime | None = None,
    cancel_at_period_end: bool = False,
    canceled_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> ProviderSubscription:
    provider = SubscriptionProvider(provider).value
    status = ProviderSubscriptionStatus(status).value
    subscription = None
    if external_subscription_id is not None:
        subscription = get_by_provider_subscription_id(
            db,
            provider,
            external_subscription_id,
        )

    values = {
        "user_id": user_id,
        "provider": provider,
        "external_customer_id": external_customer_id,
        "external_subscription_id": external_subscription_id,
        "external_product_id": external_product_id,
        "plan": plan,
        "status": status,
        "current_period_start": current_period_start,
        "current_period_end": current_period_end,
        "trial_end": trial_end,
        "cancel_at_period_end": cancel_at_period_end,
        "canceled_at": canceled_at,
        "ended_at": ended_at,
    }

    if subscription is None:
        subscription = ProviderSubscription(**values)
        db.add(subscription)
    else:
        for field, value in values.items():
            setattr(subscription, field, value)

    db.flush()
    return subscription


def get_user_provider_subscriptions(
    db: Session,
    user_id: int,
) -> list[ProviderSubscription]:
    return (
        db.query(ProviderSubscription)
        .filter(ProviderSubscription.user_id == user_id)
        .order_by(ProviderSubscription.id)
        .all()
    )