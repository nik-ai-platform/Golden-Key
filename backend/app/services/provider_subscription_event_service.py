from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.provider_subscription import SubscriptionProvider
from app.models.provider_subscription_event import (
    ProviderEventProcessingStatus,
    ProviderSubscriptionEvent,
)


@dataclass(frozen=True)
class ProviderEventRecordResult:
    event: ProviderSubscriptionEvent
    created: bool


def get_provider_event(
    db: Session,
    provider: str,
    external_event_id: str,
) -> ProviderSubscriptionEvent | None:
    return (
        db.query(ProviderSubscriptionEvent)
        .filter(
            ProviderSubscriptionEvent.provider == provider,
            ProviderSubscriptionEvent.external_event_id == external_event_id,
        )
        .one_or_none()
    )


def record_provider_event(
    db: Session,
    *,
    provider: str,
    external_event_id: str,
    event_type: str,
    external_subscription_id: str | None = None,
    received_at: datetime | None = None,
) -> ProviderEventRecordResult:
    provider = SubscriptionProvider(provider).value
    existing = get_provider_event(db, provider, external_event_id)
    if existing is not None:
        return ProviderEventRecordResult(event=existing, created=False)

    event = ProviderSubscriptionEvent(
        provider=provider,
        external_event_id=external_event_id,
        event_type=event_type,
        external_subscription_id=external_subscription_id,
        received_at=received_at or datetime.now(UTC),
        processing_status=ProviderEventProcessingStatus.RECEIVED.value,
    )
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
    except IntegrityError:
        existing = get_provider_event(db, provider, external_event_id)
        if existing is None:
            raise
        return ProviderEventRecordResult(event=existing, created=False)
    return ProviderEventRecordResult(event=event, created=True)


def mark_provider_event_processed(
    db: Session,
    event: ProviderSubscriptionEvent,
    *,
    processed_at: datetime | None = None,
) -> ProviderSubscriptionEvent:
    event.processing_status = ProviderEventProcessingStatus.PROCESSED.value
    event.processed_at = processed_at or datetime.now(UTC)
    event.error_message = None
    db.flush()
    return event


def mark_provider_event_failed(
    db: Session,
    event: ProviderSubscriptionEvent,
    error_message: str,
    *,
    processed_at: datetime | None = None,
) -> ProviderSubscriptionEvent:
    event.processing_status = ProviderEventProcessingStatus.FAILED.value
    event.processed_at = processed_at or datetime.now(UTC)
    event.error_message = error_message
    db.flush()
    return event