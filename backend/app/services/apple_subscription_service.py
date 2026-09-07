from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.provider_subscription import (
    ProviderSubscription,
    ProviderSubscriptionStatus,
)
from app.models.provider_subscription_event import ProviderEventProcessingStatus
from app.models.provider_subscription_event import ProviderSubscriptionEvent
from app.providers.apple_subscription_provider import (
    AppleSubscriptionProvider,
    VerifiedAppleNotification,
    VerifiedAppleRenewal,
    VerifiedAppleTransaction,
)
from app.services.entitlement_reconciliation_service import reconcile_premium_entitlement
from app.services.provider_subscription_event_service import (
    mark_provider_event_failed,
    mark_provider_event_processed,
    record_provider_event,
)
from app.services.provider_subscription_service import (
    create_or_update_provider_subscription,
    get_by_provider_subscription_id,
)


SUPPORTED_NOTIFICATION_TYPES = {
    "SUBSCRIBED",
    "DID_RENEW",
    "DID_CHANGE_RENEWAL_PREF",
    "DID_CHANGE_RENEWAL_STATUS",
    "OFFER_REDEEMED",
    "EXPIRED",
    "DID_FAIL_TO_RENEW",
    "GRACE_PERIOD_EXPIRED",
    "REFUND",
    "REFUND_DECLINED",
    "REFUND_REVERSED",
    "RENEWAL_EXTENDED",
    "REVOKE",
}


class AppleSubscriptionError(RuntimeError):
    pass


class AppleSubscriptionOwnershipError(AppleSubscriptionError):
    pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_stale(
    existing: ProviderSubscription,
    transaction: VerifiedAppleTransaction,
) -> bool:
    if existing.current_period_end is None:
        return False
    incoming_end = _as_utc(transaction.expires_at)
    existing_end = _as_utc(existing.current_period_end)
    if incoming_end < existing_end:
        return True
    if (
        existing.status == ProviderSubscriptionStatus.REVOKED.value
        and existing.canceled_at is not None
        and transaction.signed_at is not None
        and _as_utc(transaction.signed_at) <= _as_utc(existing.canceled_at)
    ):
        return True
    return False


def _subscription_state(
    transaction: VerifiedAppleTransaction,
    *,
    event_type: str | None,
    subtype: str | None,
    renewal: VerifiedAppleRenewal | None,
    as_of: datetime,
    existing_cancel_at_period_end: bool,
) -> tuple[str, datetime, bool, datetime | None, datetime | None]:
    period_end = _as_utc(transaction.expires_at)
    if renewal is not None and renewal.auto_renew_enabled is not None:
        cancel_at_period_end = not renewal.auto_renew_enabled
    elif subtype == "AUTO_RENEW_DISABLED":
        cancel_at_period_end = True
    elif subtype == "AUTO_RENEW_ENABLED":
        cancel_at_period_end = False
    else:
        cancel_at_period_end = existing_cancel_at_period_end

    # Revocation/refund ends access immediately. Billing grace remains active;
    # retry without grace is past due, and opt-out stays active through expiry.
    if transaction.revoked_at is not None or event_type in {"REFUND", "REVOKE"}:
        revoked_at = _as_utc(transaction.revoked_at or transaction.signed_at or as_of)
        return (
            ProviderSubscriptionStatus.REVOKED.value,
            period_end,
            False,
            revoked_at,
            revoked_at,
        )
    if event_type == "DID_FAIL_TO_RENEW":
        grace_end = renewal.grace_period_expires_at if renewal else None
        if grace_end is not None and _as_utc(grace_end) > as_of:
            return (
                ProviderSubscriptionStatus.ACTIVE.value,
                _as_utc(grace_end),
                cancel_at_period_end,
                None,
                None,
            )
        return (
            ProviderSubscriptionStatus.PAST_DUE.value,
            period_end,
            cancel_at_period_end,
            None,
            None,
        )
    if event_type == "GRACE_PERIOD_EXPIRED":
        return (
            ProviderSubscriptionStatus.EXPIRED.value,
            period_end,
            cancel_at_period_end,
            None,
            period_end,
        )
    if event_type == "EXPIRED" or period_end <= as_of:
        status = (
            ProviderSubscriptionStatus.CANCELED.value
            if subtype == "VOLUNTARY"
            else ProviderSubscriptionStatus.EXPIRED.value
        )
        return status, period_end, cancel_at_period_end, None, period_end
    return (
        ProviderSubscriptionStatus.ACTIVE.value,
        period_end,
        cancel_at_period_end,
        (
            renewal.signed_at or transaction.signed_at
            if cancel_at_period_end and renewal is not None
            else transaction.signed_at if cancel_at_period_end else None
        ),
        None,
    )


def synchronize_apple_subscription(
    db: Session,
    transaction: VerifiedAppleTransaction,
    *,
    user_id: int | None = None,
    event_type: str | None = None,
    subtype: str | None = None,
    renewal: VerifiedAppleRenewal | None = None,
    as_of: datetime | None = None,
) -> tuple[ProviderSubscription, bool]:
    existing = get_by_provider_subscription_id(
        db,
        "apple",
        transaction.original_transaction_id,
    )
    if existing is not None and user_id is not None and existing.user_id != user_id:
        raise AppleSubscriptionOwnershipError(
            "Apple subscription is already linked to another account"
        )
    resolved_user_id = existing.user_id if existing is not None else user_id
    if resolved_user_id is None:
        raise AppleSubscriptionError(
            "Apple subscription is not linked to a Golden Key account"
        )
    if existing is not None and _is_stale(existing, transaction):
        reconcile_premium_entitlement(db, resolved_user_id)
        return existing, True

    as_of = _as_utc(as_of or datetime.now(UTC))
    status, period_end, cancel_at_period_end, canceled_at, ended_at = (
        _subscription_state(
            transaction,
            event_type=event_type,
            subtype=subtype,
            renewal=renewal,
            as_of=as_of,
            existing_cancel_at_period_end=(
                existing.cancel_at_period_end if existing is not None else False
            ),
        )
    )
    subscription = create_or_update_provider_subscription(
        db,
        user_id=resolved_user_id,
        provider="apple",
        external_subscription_id=transaction.original_transaction_id,
        external_product_id=transaction.product_id,
        plan="pro",
        status=status,
        current_period_start=transaction.purchased_at,
        current_period_end=period_end,
        cancel_at_period_end=cancel_at_period_end,
        canceled_at=canceled_at,
        ended_at=ended_at,
    )
    reconcile_premium_entitlement(db, resolved_user_id, as_of=as_of)
    return subscription, False


def verify_and_synchronize_apple_transaction(
    db: Session,
    provider: AppleSubscriptionProvider,
    *,
    user_id: int,
    signed_transaction: str,
) -> ProviderSubscription:
    transaction = provider.verify_transaction(signed_transaction)
    subscription, _ = synchronize_apple_subscription(
        db,
        transaction,
        user_id=user_id,
    )
    return subscription


def process_verified_apple_notification(
    db: Session,
    notification: VerifiedAppleNotification,
) -> tuple[str, bool]:
    transaction = notification.transaction
    external_subscription_id = (
        transaction.original_transaction_id if transaction else None
    )
    recorded = record_provider_event(
        db,
        provider="apple",
        external_event_id=notification.event_id,
        event_type=(
            f"{notification.event_type}:{notification.subtype}"
            if notification.subtype
            else notification.event_type
        ),
        external_subscription_id=external_subscription_id,
    )
    db.commit()
    provider_event = (
        db.query(ProviderSubscriptionEvent)
        .filter(
            ProviderSubscriptionEvent.provider == "apple",
            ProviderSubscriptionEvent.external_event_id == notification.event_id,
        )
        .with_for_update()
        .populate_existing()
        .one()
    )
    if provider_event.processing_status in {
        ProviderEventProcessingStatus.PROCESSED.value,
        ProviderEventProcessingStatus.IGNORED.value,
    }:
        db.commit()
        return provider_event.processing_status, True

    try:
        with db.begin_nested():
            if notification.event_type not in SUPPORTED_NOTIFICATION_TYPES:
                provider_event.processing_status = (
                    ProviderEventProcessingStatus.IGNORED.value
                )
                provider_event.processed_at = datetime.now(UTC)
                db.flush()
            else:
                if transaction is None:
                    raise AppleSubscriptionError(
                        "Apple subscription notification has no transaction"
                    )
                synchronize_apple_subscription(
                    db,
                    transaction,
                    event_type=notification.event_type,
                    subtype=notification.subtype,
                    renewal=notification.renewal,
                )
                mark_provider_event_processed(db, provider_event)
    except Exception as exc:
        mark_provider_event_failed(db, provider_event, str(exc))
        db.commit()
        raise
    db.commit()
    return provider_event.processing_status, False