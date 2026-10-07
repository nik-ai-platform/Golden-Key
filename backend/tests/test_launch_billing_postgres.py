"""Synthetic PostgreSQL billing race tests; never use a production database."""

from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
from uuid import uuid4
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import DefaultClause, MetaData, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.roles import UserRole
from app.models.application_entitlement import ApplicationEntitlement
from app.models.provider_subscription import ProviderSubscription
from app.models.provider_subscription_event import ProviderSubscriptionEvent
from app.models.user import User
from app.services.entitlement_service import has_active_entitlement
from app.services.stripe_subscription_service import PremiumCheckoutConflict, create_checkout_session, process_verified_stripe_event
from test_stripe_subscription_service import FakeStripeGateway, _stripe_event, _stripe_subscription


@pytest.fixture
def billing_postgres():
    url = os.environ.get("LAUNCH_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set LAUNCH_TEST_POSTGRES_URL to a disposable loopback launch_validation database")
    parsed = make_url(url)
    assert parsed.host in {"localhost", "127.0.0.1", "::1"}
    assert parsed.database == "launch_validation"
    schema = "launch_billing_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    factory = sessionmaker(bind=engine)
    try:
        users = User.__table__.to_metadata(MetaData())
        users.c.role.server_default = DefaultClause("VIEWER")
        users.create(engine)
        for model in (ProviderSubscription, ApplicationEntitlement, ProviderSubscriptionEvent):
            model.__table__.create(engine)
        with factory() as db:
            db.add(User(id=1, username="billing_fixture", email="billing@example.com",
                        hashed_password="unused", role=UserRole.VIEWER, is_active=True))
            db.commit()
        yield factory
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def _process_concurrently(factory, events):
    barrier = Barrier(len(events))

    def process(event):
        with factory() as db:
            barrier.wait(timeout=10)
            return process_verified_stripe_event(db, FakeStripeGateway(), event)

    with ThreadPoolExecutor(max_workers=len(events)) as executor:
        return list(executor.map(process, events))


def test_concurrent_out_of_order_events_leave_latest_state(billing_postgres):
    older = _stripe_event("evt_pg_old", "customer.subscription.updated", _stripe_subscription())
    newer = _stripe_event("evt_pg_new", "customer.subscription.deleted", _stripe_subscription(status="canceled"))
    newer["created"] += 10
    _process_concurrently(billing_postgres, [older, newer])
    with billing_postgres() as db:
        assert db.query(ProviderSubscription).one().status == "canceled"
        assert not has_active_entitlement(db, 1, "premium")
        entitlement = db.query(ApplicationEntitlement).one_or_none()
        assert entitlement is None or entitlement.status == "inactive"
        assert db.query(ProviderSubscriptionEvent).count() == 2


def test_concurrent_duplicate_events_process_once(billing_postgres):
    event = _stripe_event("evt_pg_duplicate", "customer.subscription.updated", _stripe_subscription())
    results = _process_concurrently(billing_postgres, [event, event])
    assert sorted(duplicate for _, duplicate in results) == [False, True]
    with billing_postgres() as db:
        assert db.query(ProviderSubscriptionEvent).count() == 1
        assert db.query(ApplicationEntitlement).count() == 1


@pytest.mark.parametrize("status", ["active", "trialing"])
def test_persisted_premium_rejects_concurrent_checkouts_in_new_sessions(billing_postgres, status):
    with billing_postgres() as db:
        event = _stripe_event("evt_pg_checkout_guard", "customer.subscription.updated", _stripe_subscription(status=status))
        process_verified_stripe_event(db, FakeStripeGateway(), event)
    barrier = Barrier(2)

    def checkout(_):
        gateway = FakeStripeGateway()
        with billing_postgres() as db:
            barrier.wait(timeout=10)
            with pytest.raises(PremiumCheckoutConflict):
                create_checkout_session(db, gateway, user=db.get(User, 1), plan="pro_annual")
        assert not gateway.checkout_calls

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(checkout, range(2)))
    with billing_postgres() as db:
        assert db.query(ProviderSubscription).count() == 1
        assert has_active_entitlement(db, 1, "premium")


def test_concurrent_user_subscriptions_reconcile_single_entitlement(billing_postgres):
    active = _stripe_event("evt_pg_active", "customer.subscription.updated", _stripe_subscription())
    canceled = _stripe_event(
        "evt_pg_canceled", "customer.subscription.deleted",
        _stripe_subscription(id="sub_other", status="canceled"),
    )
    _process_concurrently(billing_postgres, [active, canceled])
    with billing_postgres() as db:
        assert db.query(ProviderSubscription).count() == 2
        entitlement = db.query(ApplicationEntitlement).one()
        assert entitlement.status == "active"


def test_chronology_migration_preserves_legacy_events_and_roundtrips(billing_postgres):
    event = _stripe_event("evt_pg_legacy", "customer.subscription.updated", _stripe_subscription())
    with billing_postgres() as db:
        process_verified_stripe_event(db, FakeStripeGateway(), event)
    engine = billing_postgres.kw["bind"]
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE provider_subscription_events DROP COLUMN provider_created_at"))
        before = connection.scalar(text("SELECT to_jsonb(e) FROM provider_subscription_events e"))
        business_tables = ("users", "provider_subscriptions", "application_entitlements")
        business_before = {
            name: connection.execute(text(f"SELECT to_jsonb(t) FROM {name} t ORDER BY id")).scalars().all()
            for name in business_tables
        }
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
        config.attributes["connection"] = connection
        command.stamp(config, "e7b4c2d9a610")
        command.upgrade(config, "a9b2e4d7c031")
        for table in (
            "auth_access_sessions", "auth_refresh_sessions", "auth_revoked_tokens",
            "auth_login_failures", "auth_email_verification_tokens", "auth_verified_emails",
        ):
            assert connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) == 0
        assert {
            name: connection.execute(text(f"SELECT to_jsonb(t) FROM {name} t ORDER BY id")).scalars().all()
            for name in business_tables
        } == business_before
        after = connection.scalar(text("SELECT to_jsonb(e) FROM provider_subscription_events e"))
        assert after.pop("provider_created_at") is None
        assert after == before
        command.downgrade(config, "f8a1d3c6b920")
        assert connection.scalar(text("SELECT to_jsonb(e) FROM provider_subscription_events e")) == before
        command.upgrade(config, "a9b2e4d7c031")
        assert connection.scalar(text("SELECT provider_created_at FROM provider_subscription_events")) is None
        command.downgrade(config, "e7b4c2d9a610")
        assert connection.scalar(text("SELECT to_jsonb(e) FROM provider_subscription_events e")) == before
        command.upgrade(config, "a9b2e4d7c031")
