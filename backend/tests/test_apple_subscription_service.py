from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import subscriptions as subscription_routes
from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.core.roles import UserRole
from app.database.session import get_db
from app.main import app
from app.models.application_entitlement import ApplicationEntitlement
from app.models.provider_subscription import ProviderSubscription
from app.models.provider_subscription_event import ProviderSubscriptionEvent
from app.models.user import User
from app.providers.apple_subscription_provider import (
    AppleVerificationError,
    VerifiedAppleNotification,
    VerifiedAppleRenewal,
    VerifiedAppleTransaction,
)
from app.services.apple_subscription_service import (
    AppleSubscriptionError,
    AppleSubscriptionOwnershipError,
    process_verified_apple_notification,
    synchronize_apple_subscription,
    verify_and_synchronize_apple_transaction,
)
import app.services.apple_subscription_service as apple_subscription_service
from app.services.entitlement_reconciliation_service import reconcile_premium_entitlement
from app.services.provider_subscription_event_service import record_provider_event
from app.services.provider_subscription_service import create_or_update_provider_subscription


NOW = datetime.now(UTC).replace(microsecond=0)


class FakeAppleProvider:
    def __init__(self, *, transaction=None, notification=None, error=None):
        self.transaction = transaction
        self.notification = notification
        self.error = error

    def verify_transaction(self, signed_transaction):
        if self.error:
            raise self.error
        assert signed_transaction == "signed-transaction"
        return self.transaction

    def verify_notification(self, signed_payload):
        if self.error:
            raise self.error
        assert signed_payload == "signed-notification"
        return self.notification


@pytest.fixture()
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    ProviderSubscription.__table__.create(engine)
    ApplicationEntitlement.__table__.create(engine)
    ProviderSubscriptionEvent.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.add_all(
        [
            User(
                id=1,
                username="apple_customer",
                email="apple.customer@example.com",
                hashed_password="unused",
                role=UserRole.VIEWER,
                is_active=True,
            ),
            User(
                id=2,
                username="other_customer",
                email="other.customer@example.com",
                hashed_password="unused",
                role=UserRole.VIEWER,
                is_active=True,
            ),
        ]
    )
    db.commit()
    try:
        yield db, factory
    finally:
        db.close()
        engine.dispose()


def _transaction(
    *,
    original_id="original-1",
    transaction_id="transaction-1",
    product_id="com.goldenkey.pro.monthly",
    purchased_at=None,
    expires_at=None,
    revoked_at=None,
    signed_at=None,
):
    return VerifiedAppleTransaction(
        original_transaction_id=original_id,
        transaction_id=transaction_id,
        product_id=product_id,
        billing_interval=("annual" if product_id.endswith("annual") else "monthly"),
        purchased_at=purchased_at or NOW,
        expires_at=expires_at or NOW + timedelta(days=30),
        revoked_at=revoked_at,
        signed_at=signed_at or NOW,
    )


def _notification(
    event_id,
    event_type,
    *,
    transaction=None,
    subtype=None,
    renewal=None,
):
    return VerifiedAppleNotification(
        event_id=event_id,
        event_type=event_type,
        subtype=subtype,
        transaction=transaction,
        renewal=renewal,
    )


def _link_apple(db, transaction=None):
    subscription, _ = synchronize_apple_subscription(
        db,
        transaction or _transaction(),
        user_id=1,
        as_of=NOW,
    )
    db.commit()
    return subscription


def _override_database(factory):
    def override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    return override


def _auth_user(user_id=1):
    return AuthUser(
        id=user_id,
        username="apple_customer" if user_id == 1 else "other_customer",
        email=(
            "apple.customer@example.com"
            if user_id == 1
            else "other.customer@example.com"
        ),
        role=UserRole.VIEWER,
        is_active=True,
    )


def test_valid_transaction_grants_premium_and_restore_is_idempotent(database):
    db, _ = database
    provider = FakeAppleProvider(transaction=_transaction())

    first = verify_and_synchronize_apple_transaction(
        db,
        provider,
        user_id=1,
        signed_transaction="signed-transaction",
    )
    second = verify_and_synchronize_apple_transaction(
        db,
        provider,
        user_id=1,
        signed_transaction="signed-transaction",
    )

    assert first.id == second.id
    assert db.query(ProviderSubscription).count() == 1
    entitlement = db.query(ApplicationEntitlement).one()
    assert entitlement.entitlement_key == "premium"
    assert entitlement.plan == "pro"
    assert entitlement.status == "active"


def test_cross_user_original_transaction_claim_is_rejected(database):
    db, _ = database
    _link_apple(db)

    with pytest.raises(AppleSubscriptionOwnershipError, match="another account"):
        synchronize_apple_subscription(db, _transaction(), user_id=2, as_of=NOW)

    assert db.query(ProviderSubscription).one().user_id == 1


def test_renewal_updates_existing_provider_row(database):
    db, _ = database
    _link_apple(db)
    renewed = _transaction(
        transaction_id="transaction-2",
        purchased_at=NOW + timedelta(days=30),
        expires_at=NOW + timedelta(days=60),
        signed_at=NOW + timedelta(days=30),
    )

    subscription, stale = synchronize_apple_subscription(
        db,
        renewed,
        event_type="DID_RENEW",
        as_of=NOW + timedelta(days=30),
    )

    assert stale is False
    assert db.query(ProviderSubscription).count() == 1
    assert subscription.current_period_end == renewed.expires_at
    assert subscription.external_product_id == renewed.product_id
    assert subscription.status == "active"


def test_older_transaction_cannot_regress_newer_subscription(database):
    db, _ = database
    newer = _transaction(
        transaction_id="transaction-new",
        purchased_at=NOW + timedelta(days=30),
        expires_at=NOW + timedelta(days=60),
    )
    _link_apple(db, newer)
    older = _transaction(
        transaction_id="transaction-old",
        expires_at=NOW + timedelta(days=30),
    )

    subscription, stale = synchronize_apple_subscription(
        db,
        older,
        event_type="EXPIRED",
        as_of=NOW + timedelta(days=31),
    )

    assert stale is True
    assert subscription.status == "active"
    assert subscription.current_period_end.replace(tzinfo=UTC) == newer.expires_at


def test_scheduled_cancellation_remains_active_until_expiration(database):
    db, _ = database
    renewal = VerifiedAppleRenewal(
        auto_renew_enabled=False,
        billing_retry=False,
        grace_period_expires_at=None,
    )

    subscription, _ = synchronize_apple_subscription(
        db,
        _transaction(),
        user_id=1,
        event_type="DID_CHANGE_RENEWAL_STATUS",
        subtype="AUTO_RENEW_DISABLED",
        renewal=renewal,
        as_of=NOW,
    )

    assert subscription.status == "active"
    assert subscription.cancel_at_period_end is True
    assert db.query(ApplicationEntitlement).one().status == "active"

    restored, _ = synchronize_apple_subscription(
        db,
        _transaction(),
        user_id=1,
        as_of=NOW,
    )
    assert restored.cancel_at_period_end is True


def test_billing_retry_and_grace_period_map_to_canonical_states(database):
    db, _ = database
    subscription, _ = synchronize_apple_subscription(
        db,
        _transaction(),
        user_id=1,
        event_type="DID_FAIL_TO_RENEW",
        renewal=VerifiedAppleRenewal(True, True, None),
        as_of=NOW,
    )
    assert subscription.status == "past_due"

    subscription, _ = synchronize_apple_subscription(
        db,
        _transaction(expires_at=NOW + timedelta(days=31)),
        event_type="DID_FAIL_TO_RENEW",
        subtype="GRACE_PERIOD",
        renewal=VerifiedAppleRenewal(
            True,
            True,
            NOW + timedelta(days=7),
        ),
        as_of=NOW,
    )
    assert subscription.status == "active"
    assert subscription.current_period_end == NOW + timedelta(days=7)


def test_billing_retry_without_renewal_info_is_past_due(database):
    db, _ = database
    subscription, _ = synchronize_apple_subscription(
        db,
        _transaction(),
        user_id=1,
        event_type="DID_FAIL_TO_RENEW",
        renewal=None,
        as_of=NOW,
    )
    assert subscription.status == "past_due"


@pytest.mark.parametrize(
    ("event_type", "revoked_at", "expected_status"),
    [
        ("EXPIRED", None, "expired"),
        ("REVOKE", NOW + timedelta(days=1), "revoked"),
        ("REFUND", NOW + timedelta(days=1), "revoked"),
    ],
)
def test_terminal_events_remove_apples_independent_grant(
    database,
    event_type,
    revoked_at,
    expected_status,
):
    db, _ = database
    _link_apple(db)
    transaction = _transaction(revoked_at=revoked_at)

    subscription, _ = synchronize_apple_subscription(
        db,
        transaction,
        event_type=event_type,
        as_of=NOW + timedelta(days=31) if event_type == "EXPIRED" else NOW,
    )

    assert subscription.status == expected_status
    assert db.query(ApplicationEntitlement).one().status == "inactive"


@pytest.mark.parametrize("other_provider", ["stripe", "admin"])
def test_inactive_apple_keeps_other_provider_premium(database, other_provider):
    db, _ = database
    _link_apple(db)
    other = create_or_update_provider_subscription(
        db,
        user_id=1,
        provider=other_provider,
        external_subscription_id=f"{other_provider}-subscription",
        plan="pro",
        status="active",
        current_period_start=NOW,
        current_period_end=NOW + timedelta(days=60),
    )
    reconcile_premium_entitlement(db, 1, as_of=NOW)

    synchronize_apple_subscription(
        db,
        _transaction(revoked_at=NOW),
        event_type="REVOKE",
        as_of=NOW,
    )

    entitlement = db.query(ApplicationEntitlement).one()
    assert entitlement.status == "active"
    assert entitlement.source_subscription_id == other.id


def test_notification_duplicate_is_idempotent(database):
    db, _ = database
    _link_apple(db)
    notification = _notification(
        "notification-1",
        "DID_RENEW",
        transaction=_transaction(
            transaction_id="transaction-2",
            expires_at=NOW + timedelta(days=60),
        ),
    )

    assert process_verified_apple_notification(db, notification) == (
        "processed",
        False,
    )
    assert process_verified_apple_notification(db, notification) == (
        "processed",
        True,
    )
    assert db.query(ProviderSubscriptionEvent).count() == 1


def test_unsupported_notification_is_durably_ignored(database):
    db, _ = database
    notification = _notification("notification-test", "TEST")

    assert process_verified_apple_notification(db, notification) == (
        "ignored",
        False,
    )
    assert process_verified_apple_notification(db, notification) == (
        "ignored",
        True,
    )
    assert db.query(ProviderSubscription).count() == 0


def test_supported_notification_without_transaction_is_failed(database):
    db, _ = database
    notification = _notification("notification-malformed", "DID_RENEW")

    with pytest.raises(AppleSubscriptionError, match="no transaction"):
        process_verified_apple_notification(db, notification)

    event = db.query(ProviderSubscriptionEvent).one()
    assert event.processing_status == "failed"
    assert db.query(ProviderSubscription).count() == 0


def test_received_and_failed_notifications_are_retryable(database):
    db, _ = database
    transaction = _transaction()
    notification = _notification(
        "notification-received",
        "DID_RENEW",
        transaction=transaction,
    )
    record_provider_event(
        db,
        provider="apple",
        external_event_id=notification.event_id,
        event_type=notification.event_type,
        external_subscription_id=transaction.original_transaction_id,
    )
    db.commit()
    _link_apple(db)
    assert process_verified_apple_notification(db, notification) == (
        "processed",
        False,
    )

    failed = _notification(
        "notification-failed",
        "DID_RENEW",
        transaction=_transaction(original_id="unlinked"),
    )
    with pytest.raises(AppleSubscriptionError, match="not linked"):
        process_verified_apple_notification(db, failed)
    assert (
        db.query(ProviderSubscriptionEvent)
        .filter_by(external_event_id="notification-failed")
        .one()
        .processing_status
        == "failed"
    )
    synchronize_apple_subscription(
        db,
        failed.transaction,
        user_id=1,
        as_of=NOW,
    )
    db.commit()
    assert process_verified_apple_notification(db, failed) == (
        "processed",
        False,
    )


def test_failed_notification_rolls_back_partial_subscription_update(
    database,
    monkeypatch,
):
    db, _ = database
    existing = _link_apple(db)
    original_end = existing.current_period_end
    notification = _notification(
        "notification-atomic",
        "DID_RENEW",
        transaction=_transaction(
            transaction_id="transaction-new",
            expires_at=NOW + timedelta(days=60),
        ),
    )

    def fail_reconciliation(*_args, **_kwargs):
        raise RuntimeError("reconciliation failed")

    monkeypatch.setattr(
        apple_subscription_service,
        "reconcile_premium_entitlement",
        fail_reconciliation,
    )
    with pytest.raises(RuntimeError, match="reconciliation failed"):
        process_verified_apple_notification(db, notification)

    db.refresh(existing)
    assert existing.current_period_end == original_end
    event = db.query(ProviderSubscriptionEvent).one()
    assert event.processing_status == "failed"


def test_authenticated_verify_route_uses_jwt_user_and_is_customer_safe(
    database,
    monkeypatch,
):
    _, factory = database
    provider = FakeAppleProvider(transaction=_transaction())
    monkeypatch.setattr(subscription_routes, "_apple_provider", lambda: provider)
    app.dependency_overrides[get_db] = _override_database(factory)
    app.dependency_overrides[get_current_user] = lambda: _auth_user(1)
    try:
        client = TestClient(app)
        rejected = client.post(
            "/api/v1/subscriptions/apple/verify",
            json={"signedTransaction": "signed-transaction", "user_id": 2},
        )
        response = client.post(
            "/api/v1/subscriptions/apple/verify",
            json={"signedTransaction": "signed-transaction"},
        )

        assert rejected.status_code == 422
        assert response.status_code == 200
        body = response.json()
        assert body["active"] is True
        assert body["provider_subscriptions"][0]["provider"] == "apple"
        assert "external_subscription_id" not in body["provider_subscriptions"][0]
        with factory() as db:
            assert db.query(ProviderSubscription).one().user_id == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_cross_user_verify_route_returns_conflict(database, monkeypatch):
    db, factory = database
    _link_apple(db)
    provider = FakeAppleProvider(transaction=_transaction())
    monkeypatch.setattr(subscription_routes, "_apple_provider", lambda: provider)
    app.dependency_overrides[get_db] = _override_database(factory)
    app.dependency_overrides[get_current_user] = lambda: _auth_user(2)
    try:
        response = TestClient(app).post(
            "/api/v1/subscriptions/apple/verify",
            json={"signedTransaction": "signed-transaction"},
        )
        assert response.status_code == 409
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_invalid_client_signature_does_not_mutate_database(database, monkeypatch):
    _, factory = database
    provider = FakeAppleProvider(error=AppleVerificationError("invalid"))
    monkeypatch.setattr(subscription_routes, "_apple_provider", lambda: provider)
    app.dependency_overrides[get_db] = _override_database(factory)
    app.dependency_overrides[get_current_user] = lambda: _auth_user(1)
    try:
        response = TestClient(app).post(
            "/api/v1/subscriptions/apple/verify",
            json={"signedTransaction": "signed-transaction"},
        )
        assert response.status_code == 422
        with factory() as db:
            assert db.query(ProviderSubscription).count() == 0
            assert db.query(ApplicationEntitlement).count() == 0
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_valid_notification_route_is_public(database, monkeypatch):
    db, factory = database
    _link_apple(db)
    notification = _notification(
        "notification-public",
        "DID_RENEW",
        transaction=_transaction(expires_at=NOW + timedelta(days=60)),
    )
    provider = FakeAppleProvider(notification=notification)
    monkeypatch.setattr(subscription_routes, "_apple_provider", lambda: provider)
    app.dependency_overrides[get_db] = _override_database(factory)
    try:
        response = TestClient(app).post(
            "/api/v1/subscriptions/webhooks/apple",
            json={"signedPayload": "signed-notification"},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "processed", "duplicate": False}
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_invalid_or_missing_notification_signature_persists_nothing(
    database,
    monkeypatch,
):
    _, factory = database
    provider = FakeAppleProvider(error=AppleVerificationError("invalid"))
    monkeypatch.setattr(subscription_routes, "_apple_provider", lambda: provider)
    app.dependency_overrides[get_db] = _override_database(factory)
    try:
        client = TestClient(app)
        assert client.post(
            "/api/v1/subscriptions/webhooks/apple",
            json={"signedPayload": "signed-notification"},
        ).status_code == 400
        assert client.post(
            "/api/v1/subscriptions/webhooks/apple",
            json={},
        ).status_code == 422
        with factory() as db:
            assert db.query(ProviderSubscriptionEvent).count() == 0
            assert db.query(ProviderSubscription).count() == 0
    finally:
        app.dependency_overrides.pop(get_db, None)