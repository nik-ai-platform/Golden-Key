from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.provider_subscription import ProviderSubscriptionStatus
from app.models.provider_subscription_event import ProviderEventProcessingStatus
from app.models.user import User
from app.services.entitlement_reconciliation_service import PREMIUM_ENTITLEMENT_KEY, reconcile_premium_entitlement
from app.services.entitlement_service import has_active_entitlement
from app.services.provider_subscription_event_service import (
    mark_provider_event_failed,
    mark_provider_event_processed,
    record_provider_event,
)
from app.services.provider_subscription_service import (
    create_or_update_provider_subscription,
    get_by_provider_subscription_id,
    get_user_provider_subscriptions,
)
from app.services.stripe_gateway import StripeGateway
from app.services.launch_plans import LAUNCH_CURRENCY, LAUNCH_PLANS
from app.models.provider_subscription_event import ProviderSubscriptionEvent


SUPPORTED_STRIPE_PLANS = frozenset({"pro_monthly", "pro_annual"})

SUPPORTED_SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}
SUPPORTED_INVOICE_EVENTS = {"invoice.payment_failed", "invoice.paid", "invoice.payment_succeeded"}

STRIPE_STATUS_MAP = {
    "trialing": ProviderSubscriptionStatus.TRIALING.value,
    "active": ProviderSubscriptionStatus.ACTIVE.value,
    "past_due": ProviderSubscriptionStatus.PAST_DUE.value,
    "unpaid": ProviderSubscriptionStatus.PAST_DUE.value,
    "incomplete": ProviderSubscriptionStatus.PAST_DUE.value,
    "paused": ProviderSubscriptionStatus.PAST_DUE.value,
    "canceled": ProviderSubscriptionStatus.CANCELED.value,
    "incomplete_expired": ProviderSubscriptionStatus.EXPIRED.value,
}


class StripeEventProcessingError(RuntimeError):
    pass


class PremiumCheckoutConflict(StripeEventProcessingError):
    pass


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromtimestamp(int(value), tz=UTC)


def _resource_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return _get(value, "id")


def _first_price(subscription: Any) -> Any:
    items = _get(_get(subscription, "items", {}), "data", []) or []
    if not items:
        return None
    return _get(items[0], "price")


def _first_price_id(subscription: Any) -> str | None:
    return _resource_id(_first_price(subscription))


def _first_product_id(subscription: Any) -> str | None:
    return _resource_id(_get(_first_price(subscription), "product"))


def _canonical_stripe_plan(value: Any) -> str:
    plan = str(value or "").strip().lower()
    if plan not in SUPPORTED_STRIPE_PLANS:
        raise StripeEventProcessingError("Unsupported Stripe subscription plan")
    return plan


def _plan_for_subscription(subscription: Any, existing_plan: str | None = None) -> str:
    metadata = _get(subscription, "metadata", {}) or {}
    plan = _get(metadata, "golden_key_plan")
    if plan:
        return _canonical_stripe_plan(plan)

    price_id = _first_price_id(subscription)
    for configured_plan, configured_price_id in settings.STRIPE_PRICE_IDS.items():
        if configured_price_id == price_id:
            return _canonical_stripe_plan(configured_plan)
    if existing_plan:
        return _canonical_stripe_plan(existing_plan)
    raise StripeEventProcessingError("Stripe subscription plan cannot be resolved")


def _user_id_for_subscription(db: Session, subscription: Any) -> int:
    subscription_id = _resource_id(_get(subscription, "id"))
    existing = (
        get_by_provider_subscription_id(db, "stripe", subscription_id)
        if subscription_id
        else None
    )
    metadata = _get(subscription, "metadata", {}) or {}
    raw_user_id = _get(metadata, "golden_key_user_id")
    if raw_user_id is not None:
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError) as exc:
            raise StripeEventProcessingError("Invalid Stripe user metadata") from exc
    elif existing is not None:
        user_id = existing.user_id
    else:
        raise StripeEventProcessingError("Stripe subscription has no user identity")

    if db.get(User, user_id) is None:
        raise StripeEventProcessingError("Stripe subscription user does not exist")
    return user_id


def _subscription_period(subscription: Any) -> tuple[datetime | None, datetime | None]:
    items = _get(_get(subscription, "items", {}), "data", []) or []
    boundaries = []
    for field in ("current_period_start", "current_period_end"):
        boundary = _timestamp(_get(subscription, field))
        if boundary is None and items:
            values = {_timestamp(_get(item, field)) for item in items}
            if len(values) != 1:
                raise StripeEventProcessingError("Stripe subscription period is incomplete or ambiguous")
            boundary = values.pop()
        boundaries.append(boundary)
    return boundaries[0], boundaries[1]


def synchronize_stripe_subscription(db: Session, subscription: Any):
    subscription_id = _resource_id(_get(subscription, "id"))
    if not subscription_id:
        raise StripeEventProcessingError("Stripe subscription ID is missing")

    existing = get_by_provider_subscription_id(db, "stripe", subscription_id)
    user_id = _user_id_for_subscription(db, subscription)
    if db.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(hashlib.blake2b(f"stripe-user:{user_id}".encode(), digest_size=8).digest(), "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    if existing is not None and existing.user_id != user_id:
        raise StripeEventProcessingError("Stripe subscription ownership cannot change")
    stripe_status = str(_get(subscription, "status", ""))
    status = STRIPE_STATUS_MAP.get(stripe_status)
    if status is None:
        raise StripeEventProcessingError(f"Unsupported Stripe status: {stripe_status}")
    period_start, period_end = _subscription_period(subscription)
    trial_end = _timestamp(_get(subscription, "trial_end"))
    if stripe_status == "trialing" and trial_end is not None:
        period_end = min(period_end, trial_end) if period_end is not None else trial_end
    if stripe_status in {"active", "trialing"} and period_end is None:
        raise StripeEventProcessingError("Stripe subscription entitlement expiry is missing")

    persisted = create_or_update_provider_subscription(
        db,
        user_id=user_id,
        provider="stripe",
        external_customer_id=_resource_id(_get(subscription, "customer")),
        external_subscription_id=subscription_id,
        external_product_id=_first_product_id(subscription),
        plan=_plan_for_subscription(subscription, existing.plan if existing else None),
        status=status,
        current_period_start=period_start,
        current_period_end=period_end,
        trial_end=trial_end,
        cancel_at_period_end=bool(_get(subscription, "cancel_at_period_end", False)),
        canceled_at=_timestamp(_get(subscription, "canceled_at")),
        ended_at=_timestamp(_get(subscription, "ended_at")),
    )
    reconcile_premium_entitlement(db, user_id)
    return persisted


def _current_subscription(gateway: StripeGateway, subscription_id: str) -> Any:
    subscription = gateway.retrieve_subscription(subscription_id)
    if _resource_id(_get(subscription, "id")) != subscription_id:
        raise StripeEventProcessingError("Stripe subscription response identity mismatch")
    return subscription


def create_checkout_session(
    db: Session,
    gateway: StripeGateway,
    *,
    user: User,
    plan: str,
) -> Any:
    if has_active_entitlement(db, user.id, PREMIUM_ENTITLEMENT_KEY):
        raise PremiumCheckoutConflict("Premium access already active; manage your existing subscription")
    plan = _canonical_stripe_plan(plan)
    price_id = settings.STRIPE_PRICE_IDS.get(plan)
    if not price_id or not price_id.startswith("price_"):
        raise StripeEventProcessingError("Stripe test price is not configured for this plan")
    price = gateway.retrieve_price(price_id)
    offer = LAUNCH_PLANS[plan]
    recurring = _get(price, "recurring", {}) or {}
    if (
        _resource_id(_get(price, "id")) != price_id
        or _get(price, "livemode") is not False
        or _get(price, "active") is not True
        or _get(price, "unit_amount") != offer["amount_minor"]
        or str(_get(price, "currency", "")).upper() != LAUNCH_CURRENCY
        or _get(recurring, "interval") != offer["interval"]
        or _get(recurring, "interval_count", 1) != 1
    ):
        raise StripeEventProcessingError("Stripe test price does not match the approved offer")

    customer_id = next(
        (
            item.external_customer_id
            for item in get_user_provider_subscriptions(db, user.id)
            if item.provider == "stripe" and item.external_customer_id
        ),
        None,
    )
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    return gateway.create_checkout_session(
        user_id=user.id,
        email=user.email,
        plan=plan,
        price_id=price_id,
        customer_id=customer_id,
        success_url=f"{frontend_url}/profile?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend_url}/profile?checkout=canceled",
    )


def create_billing_portal_session(
    db: Session,
    gateway: StripeGateway,
    *,
    user: User,
) -> Any:
    customer_id = next(
        (
            item.external_customer_id
            for item in get_user_provider_subscriptions(db, user.id)
            if item.provider == "stripe" and item.external_customer_id
        ),
        None,
    )
    if not customer_id:
        raise StripeEventProcessingError("No Stripe customer is linked to this account")
    return gateway.create_billing_portal_session(
        customer_id=customer_id,
        return_url=f"{settings.FRONTEND_URL.rstrip('/')}/profile",
    )


def process_verified_stripe_event(
    db: Session,
    gateway: StripeGateway,
    event: Any,
) -> tuple[str, bool]:
    event_id = str(_get(event, "id", ""))
    event_type = str(_get(event, "type", ""))
    if not event_id or not event_type:
        raise StripeEventProcessingError("Stripe event identity is missing")

    data_object = _get(_get(event, "data", {}), "object", {})
    if event_type == "checkout.session.completed" or event_type in SUPPORTED_INVOICE_EVENTS:
        external_subscription_id = _resource_id(_get(data_object, "subscription"))
        if not external_subscription_id and event_type in SUPPORTED_INVOICE_EVENTS:
            parent = _get(data_object, "parent", {}) or {}
            external_subscription_id = _resource_id(
                _get(_get(parent, "subscription_details", {}), "subscription")
            )
    else:
        external_subscription_id = _resource_id(_get(data_object, "id"))
    raw_created = _get(event, "created")
    if raw_created is not None and (type(raw_created) is not int or raw_created <= 0):
        raise StripeEventProcessingError("Invalid Stripe event timestamp")
    provider_created_at = _timestamp(raw_created)
    recorded = record_provider_event(
        db,
        provider="stripe",
        external_event_id=event_id,
        event_type=event_type,
        external_subscription_id=external_subscription_id,
    )
    db.commit()
    try:
        supported = event_type in SUPPORTED_SUBSCRIPTION_EVENTS | SUPPORTED_INVOICE_EVENTS | {"checkout.session.completed"}
        if supported and external_subscription_id:
            # Serialize all events for one subscription, including its first event.
            if db.get_bind().dialect.name == "postgresql":
                key = int.from_bytes(hashlib.blake2b(
                    ("stripe:" + external_subscription_id).encode(), digest_size=8,
                ).digest(), "big", signed=True)
                db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        db.refresh(recorded.event)
        if recorded.event.processing_status in {
            ProviderEventProcessingStatus.PROCESSED.value,
            ProviderEventProcessingStatus.IGNORED.value,
        }:
            db.commit()
            return recorded.event.processing_status, True
        recorded.event.provider_created_at = provider_created_at
        history = db.query(ProviderSubscriptionEvent).filter(
            ProviderSubscriptionEvent.provider == "stripe",
            ProviderSubscriptionEvent.external_subscription_id == external_subscription_id,
            ProviderSubscriptionEvent.id != recorded.event.id,
            ProviderSubscriptionEvent.processing_status == ProviderEventProcessingStatus.PROCESSED.value,
        ).all() if supported and external_subscription_id else []
        dated = [row.provider_created_at for row in history if row.provider_created_at]
        latest = max(value.replace(tzinfo=UTC) if value.tzinfo is None else value for value in dated) if dated else None
        if provider_created_at and latest and provider_created_at < latest:
            recorded.event.processing_status = ProviderEventProcessingStatus.IGNORED.value
            recorded.event.processed_at = datetime.now(UTC)
            db.commit()
            return ProviderEventProcessingStatus.IGNORED.value, False
        canonical_required = (
            provider_created_at is None
            or any(row.provider_created_at is None for row in history)
            or (latest is not None and latest == provider_created_at)
            or (not history and get_by_provider_subscription_id(db, "stripe", external_subscription_id) is not None)
        )
        if event_type == "checkout.session.completed" or event_type in SUPPORTED_INVOICE_EVENTS:
            if not external_subscription_id:
                raise StripeEventProcessingError("Stripe event has no subscription")
            synchronize_stripe_subscription(
                db,
                _current_subscription(gateway, external_subscription_id),
            )
            mark_provider_event_processed(db, recorded.event)
        elif event_type in SUPPORTED_SUBSCRIPTION_EVENTS:
            if not external_subscription_id:
                raise StripeEventProcessingError("Stripe event has no subscription")
            subscription = _current_subscription(gateway, external_subscription_id) if canonical_required else data_object
            synchronize_stripe_subscription(db, subscription)
            mark_provider_event_processed(db, recorded.event)
        else:
            recorded.event.processing_status = ProviderEventProcessingStatus.IGNORED.value
            recorded.event.processed_at = datetime.now(UTC)
            db.flush()
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_event = record_provider_event(
            db,
            provider="stripe",
            external_event_id=event_id,
            event_type=event_type,
            external_subscription_id=external_subscription_id,
        ).event
        failed_event.provider_created_at = provider_created_at
        mark_provider_event_failed(db, failed_event, str(exc))
        db.commit()
        raise
    return recorded.event.processing_status, False