from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.application_entitlement import ApplicationEntitlement, EntitlementStatus
from app.models.provider_subscription import ProviderSubscription
from app.models.provider_subscription_event import ProviderSubscriptionEvent
from app.models.user import User
from app.services.entitlement_service import has_active_entitlement, upsert_entitlement
from app.services.provider_subscription_event_service import (
    mark_provider_event_failed,
    mark_provider_event_processed,
    record_provider_event,
)
from app.services.provider_subscription_service import (
    create_or_update_provider_subscription,
    get_user_provider_subscriptions,
)


NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    ProviderSubscription.__table__.create(engine)
    ApplicationEntitlement.__table__.create(engine)
    ProviderSubscriptionEvent.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        User(
            id=1,
            username="subscriber",
            email="subscriber@example.com",
            hashed_password="unused",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _provider_subscription(db, **overrides):
    values = {
        "user_id": 1,
        "provider": "stripe",
        "external_subscription_id": "sub_123",
        "external_product_id": "price_pro",
        "plan": "pro_monthly",
        "status": "active",
        "current_period_start": NOW,
        "current_period_end": NOW + timedelta(days=30),
    }
    values.update(overrides)
    return create_or_update_provider_subscription(db, **values)


def test_provider_subscription_creation_and_db_only_upsert(db):
    created = _provider_subscription(db)
    updated = _provider_subscription(db, plan="elite", cancel_at_period_end=True)

    assert created.id == updated.id
    assert updated.plan == "elite"
    assert updated.cancel_at_period_end is True
    assert db.query(ProviderSubscription).count() == 1


def test_provider_subscription_identity_is_unique(db):
    _provider_subscription(db)
    db.add(
        ProviderSubscription(
            user_id=1,
            provider="stripe",
            external_subscription_id="sub_123",
            plan="pro",
            status="active",
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_multiple_null_external_subscription_ids_are_permitted(db):
    first = _provider_subscription(
        db,
        provider="admin",
        external_subscription_id=None,
    )
    second = _provider_subscription(
        db,
        provider="admin",
        external_subscription_id=None,
    )

    assert first.id != second.id
    assert db.query(ProviderSubscription).count() == 2


def test_stripe_and_apple_subscriptions_can_coexist_for_user(db):
    stripe = _provider_subscription(db)
    apple = _provider_subscription(
        db,
        provider="apple",
        external_subscription_id="sub_123",
        external_product_id="com.goldenkey.pro",
    )

    subscriptions = get_user_provider_subscriptions(db, 1)
    assert subscriptions == [stripe, apple]
    assert {item.provider for item in subscriptions} == {"stripe", "apple"}


def test_application_entitlement_creation_and_uniqueness(db):
    entitlement = upsert_entitlement(
        db,
        1,
        "premium",
        "pro_monthly",
        "active",
        starts_at=NOW,
    )
    db.add(
        ApplicationEntitlement(
            user_id=1,
            entitlement_key="premium",
            plan="elite",
            status="active",
            starts_at=NOW,
        )
    )

    assert entitlement.id is not None
    with pytest.raises(IntegrityError):
        db.flush()


@pytest.mark.parametrize(
    ("status", "starts_at", "ends_at", "expected"),
    (
        (EntitlementStatus.ACTIVE.value, NOW, None, True),
        (EntitlementStatus.INACTIVE.value, NOW, None, False),
        (EntitlementStatus.REVOKED.value, NOW, None, False),
        (EntitlementStatus.ACTIVE.value, NOW + timedelta(seconds=1), None, False),
        (EntitlementStatus.ACTIVE.value, NOW - timedelta(days=1), NOW, False),
    ),
)
def test_active_entitlement_lifecycle(db, status, starts_at, ends_at, expected):
    upsert_entitlement(
        db,
        1,
        "premium",
        "pro_monthly",
        status,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    assert has_active_entitlement(db, 1, "premium", as_of=NOW) is expected


def test_entitlement_upsert_updates_one_canonical_row(db):
    provider = _provider_subscription(db)
    first = upsert_entitlement(
        db,
        1,
        "premium",
        "pro",
        "active",
        source_provider="stripe",
        source_subscription_id=provider.id,
        starts_at=NOW,
    )
    second = upsert_entitlement(
        db,
        1,
        "premium",
        "elite",
        "active",
        source_provider="apple",
        source_subscription_id=None,
        starts_at=NOW,
    )

    assert first.id == second.id
    assert second.plan == "elite"
    assert second.source_provider == "apple"
    assert db.query(ApplicationEntitlement).count() == 1


def test_provider_event_uniqueness_and_duplicate_detection(db):
    first = record_provider_event(
        db,
        provider="stripe",
        external_event_id="evt_123",
        event_type="customer.subscription.updated",
        external_subscription_id="sub_123",
        received_at=NOW,
    )
    duplicate = record_provider_event(
        db,
        provider="stripe",
        external_event_id="evt_123",
        event_type="ignored.duplicate.payload",
        received_at=NOW,
    )

    assert first.created is True
    assert duplicate.created is False
    assert duplicate.event.id == first.event.id
    assert duplicate.event.event_type == "customer.subscription.updated"
    assert db.query(ProviderSubscriptionEvent).count() == 1


def test_provider_event_database_constraint_is_unique(db):
    record_provider_event(
        db,
        provider="apple",
        external_event_id="event-123",
        event_type="SUBSCRIBED",
        received_at=NOW,
    )
    db.add(
        ProviderSubscriptionEvent(
            provider="apple",
            external_event_id="event-123",
            event_type="SUBSCRIBED",
            received_at=NOW,
            processing_status="received",
        )
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_provider_event_processing_transitions(db):
    result = record_provider_event(
        db,
        provider="stripe",
        external_event_id="evt_transition",
        event_type="customer.subscription.updated",
        received_at=NOW,
    )

    processed = mark_provider_event_processed(db, result.event, processed_at=NOW)
    assert processed.processing_status == "processed"
    assert processed.error_message is None

    failed = mark_provider_event_failed(
        db,
        result.event,
        "temporary failure",
        processed_at=NOW,
    )
    assert failed.processing_status == "failed"
    assert failed.error_message == "temporary failure"