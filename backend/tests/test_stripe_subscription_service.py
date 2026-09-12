from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import subscriptions as subscription_routes
from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.core.config import settings
from app.core.roles import UserRole
from app.database.session import get_db
from app.main import app
from app.models.application_entitlement import ApplicationEntitlement
from app.models.provider_subscription import ProviderSubscription
from app.models.provider_subscription_event import ProviderSubscriptionEvent
from app.models.user import User
from app.services.entitlement_reconciliation_service import reconcile_premium_entitlement
from app.services.provider_subscription_event_service import record_provider_event
from app.services.provider_subscription_service import create_or_update_provider_subscription
from app.services.stripe_gateway import StripeGateway, StripeSandboxConfigurationError
from app.services.stripe_subscription_service import (
    StripeEventProcessingError,
    create_billing_portal_session,
    create_checkout_session,
    process_verified_stripe_event,
)


NOW = datetime(2026, 9, 7, 12, tzinfo=UTC)


class FakeStripeGateway:
    def __init__(self):
        self.checkout_calls = []
        self.portal_calls = []
        self.retrieve_calls = []
        self.event = None
        self.subscription = None

    def create_checkout_session(self, **kwargs):
        self.checkout_calls.append(kwargs)
        return type("Session", (), {"url": "https://checkout.stripe.test/session"})()

    def create_billing_portal_session(self, **kwargs):
        self.portal_calls.append(kwargs)
        return type("Session", (), {"url": "https://billing.stripe.test/session"})()

    def construct_webhook_event(self, payload, signature):
        if signature != "valid_test_signature":
            raise ValueError("invalid signature")
        return self.event

    def retrieve_subscription(self, subscription_id):
        self.retrieve_calls.append(subscription_id)
        return self.subscription


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
    db.add(
        User(
            id=1,
            username="stripe_customer",
            email="stripe.customer@example.com",
            hashed_password="unused",
            role=UserRole.VIEWER,
            is_active=True,
        )
    )
    db.commit()
    try:
        yield db, factory
    finally:
        db.close()
        engine.dispose()


def _stripe_subscription(status="active", plan="pro_monthly", **overrides):
    values = {
        "id": "sub_test_123",
        "customer": "cus_test_123",
        "status": status,
        "metadata": {
            "golden_key_user_id": "1",
            "golden_key_plan": plan,
        },
        "items": {
            "data": [
                {"price": {"id": "price_test_pro", "product": "prod_test_pro"}}
            ]
        },
        "current_period_start": int(NOW.timestamp()),
        "current_period_end": int((NOW + timedelta(days=30)).timestamp()),
        "trial_end": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "ended_at": None,
    }
    values.update(overrides)
    return values


def _stripe_event(event_id, event_type, data_object):
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data_object},
    }


def test_gateway_rejects_live_and_missing_secret_keys(monkeypatch):
    with pytest.raises(StripeSandboxConfigurationError):
        StripeGateway("sk_live_forbidden")
    with pytest.raises(StripeSandboxConfigurationError):
        StripeGateway("")

    monkeypatch.setattr(settings, "STRIPE_TEST_MODE_ENABLED", False)
    with pytest.raises(StripeSandboxConfigurationError):
        StripeGateway.from_settings()


def test_real_stripe_sdk_verifies_test_webhook_signature():
    secret = "whsec_test_signature_secret"
    payload = json.dumps(
        {
            "id": "evt_signature_test",
            "object": "event",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_test"}},
        },
        separators=(",", ":"),
    ).encode()
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode()}".encode()
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    gateway = StripeGateway("sk_test_local_only", secret)

    event = gateway.construct_webhook_event(
        payload,
        f"t={timestamp},v1={signature}",
    )

    assert event.id == "evt_signature_test"


@pytest.mark.parametrize(
    ("plan", "price_id"),
    (
        ("pro_monthly", "price_test_monthly"),
        ("pro_annual", "price_test_annual"),
    ),
)
def test_checkout_uses_canonical_plan_price(database, monkeypatch, plan, price_id):
    db, _ = database
    gateway = FakeStripeGateway()
    user = db.get(User, 1)
    monkeypatch.setattr(
        settings,
        "STRIPE_PRICE_IDS",
        {
            "pro_monthly": "price_test_monthly",
            "pro_annual": "price_test_annual",
        },
    )
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.test")

    checkout = create_checkout_session(db, gateway, user=user, plan=plan.upper())
    assert checkout.url == "https://checkout.stripe.test/session"
    assert gateway.checkout_calls[0]["plan"] == plan
    assert gateway.checkout_calls[0]["price_id"] == price_id
    assert gateway.checkout_calls[0]["customer_id"] is None


@pytest.mark.parametrize("plan", ("pro_monthly", "pro_annual"))
def test_checkout_sets_canonical_plan_metadata(database, monkeypatch, plan):
    db, _ = database
    user = db.get(User, 1)
    calls = []

    def create_session(**kwargs):
        calls.append(kwargs)
        return type("Session", (), {"url": "https://checkout.stripe.test/session"})()

    monkeypatch.setattr(
        "app.services.stripe_gateway.stripe.checkout.Session.create",
        create_session,
    )
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {plan: f"price_test_{plan}"})

    create_checkout_session(
        db,
        StripeGateway("sk_test_local_only"),
        user=user,
        plan=plan,
    )

    assert calls[0]["metadata"] == {
        "golden_key_user_id": "1",
        "golden_key_plan": plan,
    }
    assert calls[0]["subscription_data"]["metadata"] == calls[0]["metadata"]


def test_checkout_rejects_noncanonical_plans(database, monkeypatch):
    db, _ = database
    gateway = FakeStripeGateway()
    user = db.get(User, 1)
    monkeypatch.setattr(
        settings,
        "STRIPE_PRICE_IDS",
        {
            "pro": "price_test_legacy",
            "unknown": "price_test_unknown",
        },
    )

    for plan in ("pro", "unknown", ""):
        with pytest.raises(StripeEventProcessingError, match="Unsupported"):
            create_checkout_session(db, gateway, user=user, plan=plan)
    assert gateway.checkout_calls == []


def test_portal_uses_existing_stripe_customer(database, monkeypatch):
    db, _ = database
    gateway = FakeStripeGateway()
    user = db.get(User, 1)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.test")

    create_or_update_provider_subscription(
        db,
        user_id=1,
        provider="stripe",
        external_customer_id="cus_test_123",
        external_subscription_id="sub_test_123",
        plan="pro_monthly",
        status="active",
    )
    portal = create_billing_portal_session(db, gateway, user=user)
    assert portal.url == "https://billing.stripe.test/session"
    assert gateway.portal_calls == [
        {"customer_id": "cus_test_123", "return_url": "https://app.test/profile"}
    ]


@pytest.mark.parametrize("plan", ("pro_monthly", "pro_annual"))
def test_verified_webhook_synchronizes_subscription_and_entitlement(database, plan):
    db, _ = database
    gateway = FakeStripeGateway()
    event = _stripe_event(
        "evt_test_created",
        "customer.subscription.created",
        _stripe_subscription(plan=plan),
    )

    processing_status, duplicate = process_verified_stripe_event(db, gateway, event)

    provider = db.query(ProviderSubscription).one()
    entitlement = db.query(ApplicationEntitlement).one()
    provider_event = db.query(ProviderSubscriptionEvent).one()
    assert (processing_status, duplicate) == ("processed", False)
    assert provider.external_subscription_id == "sub_test_123"
    assert provider.external_product_id == "prod_test_pro"
    assert provider.plan == plan
    assert entitlement.entitlement_key == "premium"
    assert entitlement.plan == plan
    assert entitlement.status == "active"
    assert entitlement.source_provider == "stripe"
    assert provider_event.processing_status == "processed"


def test_duplicate_webhook_is_detected_without_reprocessing(database):
    db, _ = database
    gateway = FakeStripeGateway()
    event = _stripe_event(
        "evt_test_duplicate",
        "customer.subscription.updated",
        _stripe_subscription(),
    )
    assert process_verified_stripe_event(db, gateway, event) == ("processed", False)

    event["data"]["object"]["status"] = "canceled"
    assert process_verified_stripe_event(db, gateway, event) == ("processed", True)
    assert db.query(ProviderSubscription).one().status == "active"
    assert db.query(ProviderSubscriptionEvent).count() == 1


def test_received_webhook_resumes_after_interrupted_processing(database):
    db, _ = database
    gateway = FakeStripeGateway()
    event = _stripe_event(
        "evt_received",
        "customer.subscription.updated",
        _stripe_subscription(),
    )
    record_provider_event(
        db,
        provider="stripe",
        external_event_id="evt_received",
        event_type="customer.subscription.updated",
        external_subscription_id="sub_test_123",
    )
    db.commit()

    processing_status, duplicate = process_verified_stripe_event(db, gateway, event)

    assert (processing_status, duplicate) == ("processed", False)
    assert db.query(ProviderSubscriptionEvent).one().processing_status == "processed"


def test_checkout_webhook_retrieves_subscription(database):
    db, _ = database
    gateway = FakeStripeGateway()
    gateway.subscription = _stripe_subscription()
    event = _stripe_event(
        "evt_checkout_complete",
        "checkout.session.completed",
        {"id": "cs_test_123", "subscription": "sub_test_123"},
    )

    assert process_verified_stripe_event(db, gateway, event) == ("processed", False)
    assert gateway.retrieve_calls == ["sub_test_123"]


def test_unsupported_verified_event_is_durably_ignored(database):
    db, _ = database
    gateway = FakeStripeGateway()
    event = _stripe_event("evt_ignored", "invoice.created", {"id": "in_test"})

    assert process_verified_stripe_event(db, gateway, event) == ("ignored", False)
    assert db.query(ProviderSubscriptionEvent).one().processing_status == "ignored"


def test_failed_webhook_is_durable_and_retryable(database):
    db, _ = database
    gateway = FakeStripeGateway()
    broken = _stripe_subscription(metadata={})
    event = _stripe_event(
        "evt_retryable",
        "customer.subscription.created",
        broken,
    )

    with pytest.raises(Exception, match="user identity"):
        process_verified_stripe_event(db, gateway, event)
    assert db.query(ProviderSubscriptionEvent).one().processing_status == "failed"

    event["data"]["object"] = _stripe_subscription()
    assert process_verified_stripe_event(db, gateway, event) == ("processed", False)
    assert db.query(ProviderSubscriptionEvent).one().processing_status == "processed"


def test_canceled_subscription_does_not_grant_premium(database):
    db, _ = database
    gateway = FakeStripeGateway()
    event = _stripe_event(
        "evt_test_canceled",
        "customer.subscription.deleted",
        _stripe_subscription(status="canceled", plan="pro_annual"),
    )

    assert process_verified_stripe_event(db, gateway, event) == ("processed", False)
    assert db.query(ProviderSubscription).one().status == "canceled"
    assert db.query(ApplicationEntitlement).count() == 0


def test_stripe_cancellation_does_not_revoke_active_apple_entitlement(database):
    db, _ = database
    stripe_subscription = create_or_update_provider_subscription(
        db,
        user_id=1,
        provider="stripe",
        external_subscription_id="sub_stripe",
        plan="pro_monthly",
        status="active",
        current_period_start=NOW,
        current_period_end=NOW + timedelta(days=30),
    )
    apple_subscription = create_or_update_provider_subscription(
        db,
        user_id=1,
        provider="apple",
        external_subscription_id="sub_apple",
        plan="elite",
        status="active",
        current_period_start=NOW,
        current_period_end=NOW + timedelta(days=20),
    )
    entitlement = reconcile_premium_entitlement(db, 1, as_of=NOW)
    assert entitlement.source_subscription_id == apple_subscription.id

    stripe_subscription.status = "canceled"
    entitlement = reconcile_premium_entitlement(db, 1, as_of=NOW)
    assert entitlement.status == "active"
    assert entitlement.source_subscription_id == apple_subscription.id


def test_last_provider_cancellation_inactivates_entitlement(database):
    db, _ = database
    subscription = create_or_update_provider_subscription(
        db,
        user_id=1,
        provider="stripe",
        external_subscription_id="sub_only",
        plan="pro_monthly",
        status="active",
        current_period_start=NOW,
        current_period_end=NOW + timedelta(days=30),
    )
    reconcile_premium_entitlement(db, 1, as_of=NOW)
    subscription.status = "canceled"

    entitlement = reconcile_premium_entitlement(db, 1, as_of=NOW)
    assert entitlement.status == "inactive"
    assert entitlement.ends_at == NOW


def test_subscription_routes_require_authentication():
    client = TestClient(app)
    assert client.post("/api/v1/subscriptions/checkout-session", json={"plan": "pro"}).status_code == 401
    assert client.post("/api/v1/subscriptions/billing-portal").status_code == 401


def test_checkout_and_portal_routes_use_mocked_gateway(database, monkeypatch):
    db, factory = database
    create_or_update_provider_subscription(
        db,
        user_id=1,
        provider="stripe",
        external_customer_id="cus_test_123",
        external_subscription_id="sub_test_123",
        plan="pro_monthly",
        status="active",
    )
    db.commit()
    gateway = FakeStripeGateway()
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {"pro_monthly": "price_test_monthly"})
    monkeypatch.setattr(subscription_routes, "_stripe_gateway", lambda **_: gateway)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1,
        username="stripe_customer",
        email="stripe.customer@example.com",
        role=UserRole.VIEWER,
        is_active=True,
    )
    try:
        client = TestClient(app)
        checkout = client.post(
            "/api/v1/subscriptions/checkout-session",
            json={"plan": "pro_monthly", "price_id": "price_client_supplied"},
        )
        portal = client.post("/api/v1/subscriptions/billing-portal")
        assert checkout.status_code == 200
        assert checkout.json() == {"url": "https://checkout.stripe.test/session"}
        assert portal.status_code == 200
        assert portal.json() == {"url": "https://billing.stripe.test/session"}
        assert len(gateway.checkout_calls) == 1
        assert gateway.checkout_calls[0]["price_id"] == "price_test_monthly"
        assert len(gateway.portal_calls) == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_webhook_signature_is_verified_before_persistence(database, monkeypatch):
    _, factory = database
    gateway = FakeStripeGateway()

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(subscription_routes, "_stripe_gateway", lambda **_: gateway)
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/api/v1/subscriptions/webhooks/stripe",
            content=b"untrusted",
            headers={"Stripe-Signature": "invalid"},
        )
        assert response.status_code == 400
        with factory() as db:
            assert db.query(ProviderSubscriptionEvent).count() == 0
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_canonical_subscription_me_response(database):
    db, factory = database
    create_or_update_provider_subscription(
        db,
        user_id=1,
        provider="stripe",
        external_customer_id="cus_private",
        external_subscription_id="sub_private",
        external_product_id="price_private",
        plan="pro_monthly",
        status="active",
        current_period_start=NOW,
        current_period_end=NOW + timedelta(days=30),
    )
    reconcile_premium_entitlement(db, 1, as_of=NOW)
    db.commit()

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1,
        username="stripe_customer",
        email="stripe.customer@example.com",
        role=UserRole.VIEWER,
        is_active=True,
    )
    try:
        response = TestClient(app).get("/api/v1/subscriptions/me")
        assert response.status_code == 200
        body = response.json()
        assert body["active"] is True
        assert body["plan"] == "pro_monthly"
        assert body["provider_subscriptions"][0]["provider"] == "stripe"
        assert "external_customer_id" not in body["provider_subscriptions"][0]
        assert "external_subscription_id" not in body["provider_subscriptions"][0]
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)