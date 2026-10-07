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
from stripe import APIConnectionError

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


NOW = datetime.now(UTC)


def test_delayed_active_event_cannot_overwrite_newer_cancellation(database):
    db, _ = database
    gateway = FakeStripeGateway()
    newer = _stripe_event("evt_newer_cancel", "customer.subscription.deleted", _stripe_subscription(status="canceled"))
    older = _stripe_event("evt_older_active", "customer.subscription.updated", _stripe_subscription())
    newer["created"] += 20
    assert process_verified_stripe_event(db, gateway, newer) == ("processed", False)
    assert process_verified_stripe_event(db, gateway, older) == ("ignored", False)
    assert process_verified_stripe_event(db, gateway, older) == ("ignored", True)
    assert db.query(ProviderSubscription).one().status == "canceled"
    assert db.query(ApplicationEntitlement).count() == 0


def test_same_second_events_use_provider_current_state(database):
    db, _ = database
    gateway = FakeStripeGateway()
    first = _stripe_event("evt_first", "customer.subscription.updated", _stripe_subscription())
    second = _stripe_event("evt_second", "customer.subscription.deleted", _stripe_subscription(status="canceled"))
    assert process_verified_stripe_event(db, gateway, first) == ("processed", False)
    gateway.subscription = _stripe_subscription(status="canceled")
    assert process_verified_stripe_event(db, gateway, second) == ("processed", False)
    assert gateway.retrieve_calls == ["sub_test_123"]
    assert db.query(ProviderSubscription).one().status == "canceled"


@pytest.mark.parametrize("status", ["trialing", "active", "past_due", "canceled", "incomplete_expired"])
def test_invoice_events_reconcile_current_provider_status(database, status):
    db, _ = database
    gateway = FakeStripeGateway()
    gateway.subscription = _stripe_subscription(status=status)
    event = _stripe_event("evt_invoice", "invoice.payment_failed", {"id": "in_test", "subscription": "sub_test_123"})
    assert process_verified_stripe_event(db, gateway, event) == ("processed", False)
    entitlement = db.query(ApplicationEntitlement).one_or_none()
    assert (entitlement is not None and entitlement.status == "active") == (status in {"trialing", "active"})


def test_failed_event_retry_cannot_overwrite_later_reactivation(database):
    db, _ = database
    gateway = FakeStripeGateway()
    old = _stripe_event("evt_old_failure", "customer.subscription.updated", _stripe_subscription(metadata={}))
    with pytest.raises(StripeEventProcessingError):
        process_verified_stripe_event(db, gateway, old)
    newer = _stripe_event("evt_reactivated", "customer.subscription.updated", _stripe_subscription())
    newer["created"] += 10
    assert process_verified_stripe_event(db, gateway, newer) == ("processed", False)
    old["data"]["object"] = _stripe_subscription(status="past_due")
    assert process_verified_stripe_event(db, gateway, old) == ("ignored", False)
    assert db.query(ProviderSubscription).one().status == "active"


@pytest.mark.parametrize("field,value", [
    ("id", "price_wrong"), ("unit_amount", 1), ("currency", "eur"), ("livemode", True), ("active", False),
    ("recurring", {"interval": "week", "interval_count": 1}),
])
def test_checkout_rejects_unconfirmed_provider_price(database, monkeypatch, field, value):
    db, _ = database
    gateway = FakeStripeGateway()
    price = gateway.retrieve_price("price_test_monthly")
    price[field] = value
    monkeypatch.setattr(gateway, "retrieve_price", lambda _: price)
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {"pro_monthly": "price_test_monthly"})
    with pytest.raises(StripeEventProcessingError, match="approved offer"):
        create_checkout_session(db, gateway, user=db.get(User, 1), plan="pro_monthly")
    assert not gateway.checkout_calls


@pytest.mark.parametrize("status", ["active", "trialing"])
@pytest.mark.parametrize("provider", ["stripe", "apple"])
def test_checkout_rejects_existing_canonical_premium_before_provider_calls(database, monkeypatch, status, provider):
    db, _ = database
    create_or_update_provider_subscription(
        db, user_id=1, provider=provider, external_subscription_id="existing_subscription",
        plan="pro_monthly", status=status, current_period_start=NOW - timedelta(days=1),
        current_period_end=NOW + timedelta(days=7), trial_end=NOW + timedelta(days=7),
    )
    reconcile_premium_entitlement(db, 1)
    db.commit()
    gateway = FakeStripeGateway()
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {"pro_monthly": "price_test_monthly"})
    monkeypatch.setattr(gateway, "retrieve_price", lambda _: pytest.fail("Existing Premium must not call Stripe"))
    with pytest.raises(StripeEventProcessingError, match="Premium access already active"):
        create_checkout_session(db, gateway, user=db.get(User, 1), plan="pro_monthly")
    assert not gateway.checkout_calls


@pytest.mark.parametrize("status", ["canceled", "past_due", "expired"])
def test_checkout_remains_available_without_active_premium(database, monkeypatch, status):
    db, _ = database
    create_or_update_provider_subscription(
        db, user_id=1, provider="stripe", external_subscription_id="lapsed_subscription",
        plan="pro_monthly", status=status, current_period_start=NOW - timedelta(days=30),
        current_period_end=NOW - timedelta(days=1),
    )
    reconcile_premium_entitlement(db, 1)
    db.commit()
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {"pro_monthly": "price_test_monthly"})
    gateway = FakeStripeGateway()
    create_checkout_session(db, gateway, user=db.get(User, 1), plan="pro_monthly")
    assert len(gateway.checkout_calls) == 1


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_checkout_route_conflict_keeps_existing_billing_available(database, monkeypatch, status):
    db, factory = database
    create_or_update_provider_subscription(
        db, user_id=1, provider="stripe", external_customer_id="cus_existing",
        external_subscription_id="sub_existing", plan="pro_monthly", status=status,
        current_period_start=NOW - timedelta(days=1), current_period_end=NOW + timedelta(days=7),
    )
    reconcile_premium_entitlement(db, 1)
    db.commit()
    gateway = FakeStripeGateway()
    monkeypatch.setattr(subscription_routes, "_stripe_gateway", lambda **_: gateway)

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1, username="stripe_customer", email="stripe.customer@example.com",
        role=UserRole.VIEWER, is_active=True,
    )
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/subscriptions/checkout-session", json={"plan": "pro_monthly"})
            assert response.status_code == 409
            assert "Premium access already active" in response.json()["detail"]
            assert not gateway.checkout_calls
            assert client.post("/api/v1/subscriptions/billing-portal").status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_provider_retrieval_must_match_requested_subscription(database):
    db, _ = database
    gateway = FakeStripeGateway()
    gateway.subscription = _stripe_subscription(id="sub_wrong")
    event = _stripe_event("evt_wrong_identity", "invoice.paid", {"id": "in_test", "subscription": "sub_test_123"})
    with pytest.raises(StripeEventProcessingError, match="identity mismatch"):
        process_verified_stripe_event(db, gateway, event)
    assert db.query(ProviderSubscription).count() == 0
    assert db.query(ProviderSubscriptionEvent).one().processing_status == "failed"


def test_current_sdk_item_periods_set_bounded_entitlement(database):
    db, _ = database
    subscription = _stripe_subscription()
    start = subscription.pop("current_period_start")
    end = subscription.pop("current_period_end")
    subscription["items"]["data"][0].update(current_period_start=start, current_period_end=end)
    event = _stripe_event("evt_item_periods", "customer.subscription.updated", subscription)
    assert process_verified_stripe_event(db, FakeStripeGateway(), event) == ("processed", False)
    entitlement = db.query(ApplicationEntitlement).one()
    assert entitlement.ends_at.replace(tzinfo=UTC) == datetime.fromtimestamp(end, UTC)


def test_trial_end_bounds_entitlement_without_item_periods(database):
    db, _ = database
    trial_end = int((NOW + timedelta(days=7)).timestamp())
    subscription = _stripe_subscription(status="trialing", trial_end=trial_end)
    subscription.pop("current_period_start")
    subscription.pop("current_period_end")
    event = _stripe_event("evt_trial_expiry", "customer.subscription.updated", subscription)
    process_verified_stripe_event(db, FakeStripeGateway(), event)
    assert db.query(ApplicationEntitlement).one().ends_at.replace(tzinfo=UTC) == datetime.fromtimestamp(trial_end, UTC)


def test_cancellation_without_period_fields_still_revokes_access(database):
    db, _ = database
    first = _stripe_event("evt_cancel_first", "customer.subscription.updated", _stripe_subscription())
    process_verified_stripe_event(db, FakeStripeGateway(), first)
    subscription = _stripe_subscription(status="canceled")
    subscription.pop("current_period_start")
    subscription.pop("current_period_end")
    later = _stripe_event("evt_cancel_missing_period", "customer.subscription.deleted", subscription)
    later["created"] += 10
    process_verified_stripe_event(db, FakeStripeGateway(), later)
    assert db.query(ApplicationEntitlement).one().status == "inactive"


@pytest.mark.parametrize("ambiguous", [False, True])
def test_active_subscription_without_unambiguous_expiry_fails_closed(database, ambiguous):
    db, _ = database
    subscription = _stripe_subscription()
    subscription.pop("current_period_start")
    end = subscription.pop("current_period_end")
    if ambiguous:
        subscription["items"]["data"] = [
            {"current_period_start": int(NOW.timestamp()), "current_period_end": end},
            {"current_period_start": int(NOW.timestamp()), "current_period_end": end + 100},
        ]
    event = _stripe_event("evt_missing_expiry", "customer.subscription.updated", subscription)
    with pytest.raises(StripeEventProcessingError, match="period|expiry"):
        process_verified_stripe_event(db, FakeStripeGateway(), event)
    assert db.query(ApplicationEntitlement).count() == 0


def test_checkout_provider_error_is_sanitized_and_retryable(database, monkeypatch):
    db, _ = database
    gateway = FakeStripeGateway()

    def unavailable(_):
        raise APIConnectionError("synthetic-sensitive-provider-message")

    monkeypatch.setattr(gateway, "retrieve_price", unavailable)
    monkeypatch.setattr(subscription_routes, "_stripe_gateway", lambda: gateway)
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {"pro_monthly": "price_test_monthly"})
    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1, username="stripe_customer", email="stripe.customer@example.com",
        role=UserRole.VIEWER, is_active=True,
    )
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/subscriptions/checkout-session", json={"plan": "pro_monthly"})
        assert response.status_code == 503
        assert response.json()["detail"] == "Billing provider temporarily unavailable"
        assert "synthetic-sensitive" not in response.text
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


class RecordingStripeClient:
    instances = []

    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.checkout_calls = []
        self.portal_calls = []
        self.retrieve_calls = []
        self.v1 = type("V1", (), {})()
        self.v1.checkout = type("Checkout", (), {})()
        self.v1.checkout.sessions = type("Sessions", (), {})()
        self.v1.checkout.sessions.create = self._create_checkout_session
        self.v1.billing_portal = type("BillingPortal", (), {})()
        self.v1.billing_portal.sessions = type("Sessions", (), {})()
        self.v1.billing_portal.sessions.create = self._create_portal_session
        self.v1.subscriptions = type("Subscriptions", (), {})()
        self.v1.subscriptions.retrieve = self._retrieve_subscription
        self.v1.prices = type("Prices", (), {})()
        self.v1.prices.retrieve = lambda price_id: {
            "id": price_id, "active": True, "livemode": False, "currency": "usd",
            "unit_amount": 7999 if "annual" in price_id else 1000,
            "recurring": {"interval": "year" if "annual" in price_id else "month", "interval_count": 1},
        }
        self.instances.append(self)

    def _create_checkout_session(self, params=None, options=None):
        self.checkout_calls.append((params, options))
        return type("Session", (), {"url": "https://checkout.stripe.test/session"})()

    def _create_portal_session(self, params=None, options=None):
        self.portal_calls.append((params, options))
        return type("Session", (), {"url": "https://billing.stripe.test/session"})()

    def _retrieve_subscription(self, subscription_id, params=None, options=None):
        self.retrieve_calls.append((subscription_id, params, options))
        return {"id": subscription_id}


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

    def retrieve_price(self, price_id):
        annual = "annual" in price_id
        return {
            "id": price_id, "active": True, "livemode": False, "currency": "usd",
            "unit_amount": 7999 if annual else 1000,
            "recurring": {"interval": "year" if annual else "month", "interval_count": 1},
        }


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
        "created": int(NOW.timestamp()),
        "data": {"object": data_object},
    }


@pytest.mark.parametrize("secret_key", ("sk_test_allowed", "rk_test_allowed"))
def test_gateway_accepts_test_secret_keys(monkeypatch, secret_key):
    monkeypatch.setattr("app.services.stripe_gateway.stripe.StripeClient", RecordingStripeClient)
    gateway = StripeGateway(secret_key)

    assert gateway.client.secret_key == secret_key


@pytest.mark.parametrize(
    "secret_key",
    ("sk_live_forbidden", "rk_live_forbidden", "", "invalid_key"),
)
def test_gateway_rejects_live_missing_and_malformed_secret_keys(secret_key):
    with pytest.raises(StripeSandboxConfigurationError):
        StripeGateway(secret_key)


def test_gateway_requires_enabled_sandbox(monkeypatch):

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
    monkeypatch.setattr(
        "app.services.stripe_gateway.stripe.StripeClient",
        RecordingStripeClient,
    )
    monkeypatch.setattr(settings, "STRIPE_PRICE_IDS", {plan: f"price_test_{plan}"})

    gateway = StripeGateway("sk_test_local_only")
    create_checkout_session(
        db,
        gateway,
        user=user,
        plan=plan,
    )

    params, options = gateway.client.checkout_calls[0]
    assert options is None
    assert params["mode"] == "subscription"
    assert params["line_items"] == [{"price": f"price_test_{plan}", "quantity": 1}]
    assert params["customer_email"] == user.email
    assert "customer" not in params
    assert params["metadata"] == {
        "golden_key_user_id": "1",
        "golden_key_plan": plan,
    }
    assert params["subscription_data"] == {
        "metadata": params["metadata"],
        "trial_period_days": 7,
    }


def test_gateway_prefers_customer_and_uses_client_for_portal_and_retrieval(monkeypatch):
    monkeypatch.setattr(
        "app.services.stripe_gateway.stripe.StripeClient",
        RecordingStripeClient,
    )
    gateway = StripeGateway("rk_test_local_only")

    gateway.create_checkout_session(
        user_id=1,
        email="stripe.customer@example.com",
        plan="pro_monthly",
        price_id="price_test_monthly",
        success_url="https://app.test/success",
        cancel_url="https://app.test/cancel",
        customer_id="cus_test_123",
    )
    gateway.create_billing_portal_session(
        customer_id="cus_test_123",
        return_url="https://app.test/profile",
    )
    gateway.retrieve_subscription("sub_test_123")

    checkout_params, _ = gateway.client.checkout_calls[0]
    assert checkout_params["customer"] == "cus_test_123"
    assert "customer_email" not in checkout_params
    assert gateway.client.portal_calls == [
        ({"customer": "cus_test_123", "return_url": "https://app.test/profile"}, None)
    ]
    assert gateway.client.retrieve_calls == [
        ("sub_test_123", {"expand": ["items.data.price"]}, None)
    ]


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