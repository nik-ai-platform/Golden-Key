from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.providers.apple_subscription_provider import (
    AppleSubscriptionConfigurationError,
    AppleSubscriptionProvider,
    AppleVerificationError,
)


class FakeVerifier:
    def __init__(self, transaction=None, notification=None, renewal=None):
        self.transaction = transaction
        self.notification = notification
        self.renewal = renewal

    def verify_and_decode_signed_transaction(self, _):
        if isinstance(self.transaction, Exception):
            raise self.transaction
        return self.transaction

    def verify_and_decode_notification(self, _):
        if isinstance(self.notification, Exception):
            raise self.notification
        return self.notification

    def verify_and_decode_renewal_info(self, _):
        if isinstance(self.renewal, Exception):
            raise self.renewal
        return self.renewal


def _transaction(**overrides):
    values = {
        "bundleId": "com.goldenkey.test",
        "environment": "Sandbox",
        "productId": "com.goldenkey.pro.monthly",
        "originalTransactionId": "original-1",
        "transactionId": "transaction-1",
        "purchaseDate": 1_788_782_400_000,
        "expiresDate": 1_791_460_800_000,
        "revocationDate": None,
        "signedDate": 1_788_782_401_000,
        "type": "Auto-Renewable Subscription",
        "rawType": "Auto-Renewable Subscription",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _provider(verifier):
    return AppleSubscriptionProvider(
        verifier,
        bundle_id="com.goldenkey.test",
        monthly_product_id="com.goldenkey.pro.monthly",
        annual_product_id="com.goldenkey.pro.annual",
    )


def test_apple_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "APPLE_SUBSCRIPTIONS_ENABLED", False)
    with pytest.raises(AppleSubscriptionConfigurationError, match="disabled"):
        AppleSubscriptionProvider.from_settings()


def test_non_sandbox_and_missing_configuration_are_rejected(monkeypatch):
    monkeypatch.setattr(settings, "APPLE_SUBSCRIPTIONS_ENABLED", True)
    monkeypatch.setattr(settings, "APPLE_APP_STORE_ENVIRONMENT", "production")
    with pytest.raises(AppleSubscriptionConfigurationError, match="sandbox"):
        AppleSubscriptionProvider.from_settings()

    with pytest.raises(AppleSubscriptionConfigurationError, match="bundle ID"):
        AppleSubscriptionProvider(
            FakeVerifier(),
            bundle_id="",
            monthly_product_id="monthly",
            annual_product_id="annual",
        )

    monkeypatch.setattr(settings, "APPLE_APP_STORE_ENVIRONMENT", "sandbox")
    monkeypatch.setattr(settings, "APPLE_ROOT_CA_PATHS", [])
    with pytest.raises(AppleSubscriptionConfigurationError, match="root CA"):
        AppleSubscriptionProvider.from_settings()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"bundleId": "wrong.bundle"}, "bundle ID"),
        ({"environment": "Production"}, "environment"),
        ({"productId": "unknown.product"}, "Unknown"),
    ],
)
def test_verified_transaction_fails_closed_for_invalid_claims(overrides, message):
    provider = _provider(FakeVerifier(transaction=_transaction(**overrides)))
    with pytest.raises(AppleVerificationError, match=message):
        provider.verify_transaction("signed-transaction")


def test_valid_verified_transaction_is_normalized():
    provider = _provider(FakeVerifier(transaction=_transaction()))

    transaction = provider.verify_transaction("signed-transaction")

    assert transaction.original_transaction_id == "original-1"
    assert transaction.transaction_id == "transaction-1"
    assert transaction.billing_interval == "monthly"


def test_non_subscription_transaction_fails_closed():
    provider = _provider(
        FakeVerifier(transaction=_transaction(type="Consumable", rawType="Consumable"))
    )
    with pytest.raises(AppleVerificationError, match="auto-renewable"):
        provider.verify_transaction("signed-transaction")


def test_invalid_and_missing_transaction_signatures_fail_closed():
    provider = _provider(FakeVerifier(transaction=ValueError("bad signature")))
    with pytest.raises(AppleVerificationError, match="signature"):
        provider.verify_transaction("untrusted")
    with pytest.raises(AppleVerificationError, match="required"):
        provider.verify_transaction("")


@pytest.mark.parametrize(
    ("bundle_id", "environment", "message"),
    [
        ("wrong.bundle", "Sandbox", "bundle ID"),
        ("com.goldenkey.test", "Production", "environment"),
    ],
)
def test_notification_envelope_claims_are_revalidated(
    bundle_id,
    environment,
    message,
):
    notification = SimpleNamespace(
        notificationUUID="notification-1",
        notificationType="DID_RENEW",
        subtype=None,
        data=SimpleNamespace(
            bundleId=bundle_id,
            environment=environment,
            signedTransactionInfo=None,
            signedRenewalInfo=None,
        ),
    )
    provider = _provider(FakeVerifier(notification=notification))

    with pytest.raises(AppleVerificationError, match=message):
        provider.verify_notification("signed-notification")


def test_verified_notification_decodes_nested_transaction_and_renewal():
    notification = SimpleNamespace(
        notificationUUID="notification-1",
        notificationType="DID_CHANGE_RENEWAL_STATUS",
        rawNotificationType="DID_CHANGE_RENEWAL_STATUS",
        subtype="AUTO_RENEW_DISABLED",
        rawSubtype="AUTO_RENEW_DISABLED",
        data=SimpleNamespace(
            bundleId="com.goldenkey.test",
            environment="Sandbox",
            signedTransactionInfo="nested-transaction",
            signedRenewalInfo="nested-renewal",
        ),
    )
    renewal = SimpleNamespace(
        environment="Sandbox",
        rawEnvironment="Sandbox",
        productId="com.goldenkey.pro.monthly",
        autoRenewProductId="com.goldenkey.pro.monthly",
        autoRenewStatus=0,
        isInBillingRetryPeriod=False,
        gracePeriodExpiresDate=None,
        signedDate=1_788_782_402_000,
    )
    provider = _provider(
        FakeVerifier(
            transaction=_transaction(),
            notification=notification,
            renewal=renewal,
        )
    )

    verified = provider.verify_notification("signed-notification")

    assert verified.event_id == "notification-1"
    assert verified.transaction.original_transaction_id == "original-1"
    assert verified.renewal.auto_renew_enabled is False
    assert verified.renewal.signed_at is not None


def test_unknown_verified_notification_uses_raw_type_for_safe_ignoring():
    notification = SimpleNamespace(
        notificationUUID="notification-future",
        notificationType=None,
        rawNotificationType="FUTURE_EVENT",
        subtype=None,
        rawSubtype=None,
        data=None,
    )
    provider = _provider(FakeVerifier(notification=notification))

    verified = provider.verify_notification("signed-notification")

    assert verified.event_type == "FUTURE_EVENT"