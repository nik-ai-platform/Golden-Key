from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.application_entitlement import ApplicationEntitlement, EntitlementStatus
from app.models.provider_subscription import ProviderSubscription, ProviderSubscriptionStatus
from app.services.entitlement_service import get_entitlement, upsert_entitlement
from app.services.provider_subscription_service import get_user_provider_subscriptions


PREMIUM_ENTITLEMENT_KEY = "premium"
ACTIVE_PROVIDER_STATUSES = {
    ProviderSubscriptionStatus.TRIALING.value,
    ProviderSubscriptionStatus.ACTIVE.value,
}
PLAN_RANK = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "elite": 3,
    "enterprise": 4,
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_active(subscription: ProviderSubscription, as_of: datetime) -> bool:
    if subscription.status not in ACTIVE_PROVIDER_STATUSES:
        return False
    if subscription.current_period_start is not None:
        if _as_utc(subscription.current_period_start) > as_of:
            return False
    if subscription.current_period_end is not None:
        if _as_utc(subscription.current_period_end) <= as_of:
            return False
    return True


def reconcile_premium_entitlement(
    db: Session,
    user_id: int,
    *,
    as_of: datetime | None = None,
) -> ApplicationEntitlement | None:
    as_of = _as_utc(as_of or datetime.now(UTC))
    subscriptions = get_user_provider_subscriptions(db, user_id)
    active = [item for item in subscriptions if _is_active(item, as_of)]

    if active:
        source = max(
            active,
            key=lambda item: (
                PLAN_RANK.get(item.plan.lower(), -1),
                item.current_period_end is None,
                _as_utc(item.current_period_end) if item.current_period_end else as_of,
                item.id,
            ),
        )
        return upsert_entitlement(
            db,
            user_id,
            PREMIUM_ENTITLEMENT_KEY,
            source.plan,
            EntitlementStatus.ACTIVE.value,
            source_provider=source.provider,
            source_subscription_id=source.id,
            starts_at=source.current_period_start or source.created_at or as_of,
            ends_at=source.current_period_end,
        )

    existing = get_entitlement(db, user_id, PREMIUM_ENTITLEMENT_KEY)
    if existing is None:
        return None
    return upsert_entitlement(
        db,
        user_id,
        PREMIUM_ENTITLEMENT_KEY,
        existing.plan,
        EntitlementStatus.INACTIVE.value,
        source_provider=existing.source_provider,
        source_subscription_id=existing.source_subscription_id,
        starts_at=existing.starts_at,
        ends_at=as_of,
    )