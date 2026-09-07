from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.application_entitlement import ApplicationEntitlement, EntitlementStatus


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_entitlement(
    db: Session,
    user_id: int,
    entitlement_key: str,
) -> ApplicationEntitlement | None:
    return (
        db.query(ApplicationEntitlement)
        .filter(
            ApplicationEntitlement.user_id == user_id,
            ApplicationEntitlement.entitlement_key == entitlement_key,
        )
        .one_or_none()
    )


def has_active_entitlement(
    db: Session,
    user_id: int,
    entitlement_key: str,
    as_of: datetime | None = None,
) -> bool:
    entitlement = get_entitlement(db, user_id, entitlement_key)
    if entitlement is None or entitlement.status != EntitlementStatus.ACTIVE.value:
        return False

    as_of = _as_utc(as_of or datetime.now(UTC))
    starts_at = _as_utc(entitlement.starts_at)
    ends_at = _as_utc(entitlement.ends_at) if entitlement.ends_at else None
    return starts_at <= as_of and (ends_at is None or ends_at > as_of)


def upsert_entitlement(
    db: Session,
    user_id: int,
    entitlement_key: str,
    plan: str,
    status: str,
    source_provider: str | None = None,
    source_subscription_id: int | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> ApplicationEntitlement:
    status = EntitlementStatus(status).value
    entitlement = get_entitlement(db, user_id, entitlement_key)
    starts_at = _as_utc(starts_at or datetime.now(UTC))
    ends_at = _as_utc(ends_at) if ends_at else None

    if entitlement is None:
        entitlement = ApplicationEntitlement(
            user_id=user_id,
            entitlement_key=entitlement_key,
            plan=plan,
            status=status,
            source_provider=source_provider,
            source_subscription_id=source_subscription_id,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        db.add(entitlement)
    else:
        entitlement.plan = plan
        entitlement.status = status
        entitlement.source_provider = source_provider
        entitlement.source_subscription_id = source_subscription_id
        entitlement.starts_at = starts_at
        entitlement.ends_at = ends_at

    db.flush()
    return entitlement