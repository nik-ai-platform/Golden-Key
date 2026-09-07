from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.signed_data_verifier import (
    SignedDataVerifier,
    VerificationException,
)

from app.core.config import settings


class AppleSubscriptionConfigurationError(RuntimeError):
    pass


class AppleVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedAppleTransaction:
    original_transaction_id: str
    transaction_id: str
    product_id: str
    billing_interval: str
    purchased_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    signed_at: datetime | None


@dataclass(frozen=True)
class VerifiedAppleRenewal:
    auto_renew_enabled: bool | None
    billing_retry: bool
    grace_period_expires_at: datetime | None
    signed_at: datetime | None = None


@dataclass(frozen=True)
class VerifiedAppleNotification:
    event_id: str
    event_type: str
    subtype: str | None
    transaction: VerifiedAppleTransaction | None
    renewal: VerifiedAppleRenewal | None


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _milliseconds(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)


class AppleSubscriptionProvider:
    def __init__(
        self,
        verifier: Any,
        *,
        bundle_id: str,
        monthly_product_id: str,
        annual_product_id: str,
        environment: str = "sandbox",
    ):
        if environment.lower() != "sandbox":
            raise AppleSubscriptionConfigurationError(
                "Apple subscriptions require the sandbox environment"
            )
        if not bundle_id:
            raise AppleSubscriptionConfigurationError("Apple bundle ID is required")
        if not monthly_product_id or not annual_product_id:
            raise AppleSubscriptionConfigurationError(
                "Apple subscription product IDs are required"
            )
        if monthly_product_id == annual_product_id:
            raise AppleSubscriptionConfigurationError(
                "Apple monthly and annual product IDs must differ"
            )
        self.verifier = verifier
        self.bundle_id = bundle_id
        self.environment = environment.lower()
        self.product_intervals = {
            monthly_product_id: "monthly",
            annual_product_id: "annual",
        }

    @classmethod
    def from_settings(cls) -> "AppleSubscriptionProvider":
        if not settings.APPLE_SUBSCRIPTIONS_ENABLED:
            raise AppleSubscriptionConfigurationError(
                "Apple subscriptions are disabled"
            )
        if settings.APPLE_APP_STORE_ENVIRONMENT.lower() != "sandbox":
            raise AppleSubscriptionConfigurationError(
                "Apple subscriptions require the sandbox environment"
            )
        if not settings.APPLE_ROOT_CA_PATHS:
            raise AppleSubscriptionConfigurationError(
                "Apple root CA certificate paths are required"
            )
        try:
            root_certificates = [
                Path(path).expanduser().read_bytes()
                for path in settings.APPLE_ROOT_CA_PATHS
            ]
        except OSError as exc:
            raise AppleSubscriptionConfigurationError(
                "Apple root CA certificate could not be read"
            ) from exc
        verifier = SignedDataVerifier(
            root_certificates,
            settings.APPLE_ENABLE_ONLINE_CHECKS,
            Environment.SANDBOX,
            settings.APPLE_BUNDLE_ID,
            settings.APPLE_APPLE_ID,
        )
        return cls(
            verifier,
            bundle_id=settings.APPLE_BUNDLE_ID,
            monthly_product_id=settings.APPLE_PRO_MONTHLY_PRODUCT_ID,
            annual_product_id=settings.APPLE_PRO_ANNUAL_PRODUCT_ID,
            environment=settings.APPLE_APP_STORE_ENVIRONMENT,
        )

    def verify_transaction(self, signed_transaction: str) -> VerifiedAppleTransaction:
        if not signed_transaction:
            raise AppleVerificationError("Signed Apple transaction is required")
        try:
            decoded = self.verifier.verify_and_decode_signed_transaction(
                signed_transaction
            )
        except (VerificationException, ValueError, TypeError) as exc:
            raise AppleVerificationError("Apple transaction signature is invalid") from exc
        return self._normalize_transaction(decoded)

    def verify_notification(self, signed_payload: str) -> VerifiedAppleNotification:
        if not signed_payload:
            raise AppleVerificationError("Signed Apple notification is required")
        try:
            decoded = self.verifier.verify_and_decode_notification(signed_payload)
        except (VerificationException, ValueError, TypeError) as exc:
            raise AppleVerificationError("Apple notification signature is invalid") from exc

        event_id = str(getattr(decoded, "notificationUUID", "") or "")
        event_type = str(
            _enum_value(getattr(decoded, "notificationType", None))
            or getattr(decoded, "rawNotificationType", None)
            or ""
        )
        subtype_value = (
            _enum_value(getattr(decoded, "subtype", None))
            or getattr(decoded, "rawSubtype", None)
        )
        if not event_id or not event_type:
            raise AppleVerificationError("Apple notification identity is missing")

        data = getattr(decoded, "data", None)
        transaction = None
        renewal = None
        if data is not None:
            self._validate_identity(
                getattr(data, "bundleId", None),
                getattr(data, "environment", None),
            )
            signed_transaction = getattr(data, "signedTransactionInfo", None)
            if signed_transaction:
                transaction = self.verify_transaction(signed_transaction)
            signed_renewal = getattr(data, "signedRenewalInfo", None)
            if signed_renewal:
                renewal = self._verify_renewal(signed_renewal)
        return VerifiedAppleNotification(
            event_id=event_id,
            event_type=event_type,
            subtype=str(subtype_value) if subtype_value else None,
            transaction=transaction,
            renewal=renewal,
        )

    def _normalize_transaction(self, decoded: Any) -> VerifiedAppleTransaction:
        self._validate_identity(
            getattr(decoded, "bundleId", None),
            getattr(decoded, "environment", None),
        )
        product_id = str(getattr(decoded, "productId", "") or "")
        billing_interval = self.product_intervals.get(product_id)
        if billing_interval is None:
            raise AppleVerificationError("Unknown Apple subscription product")
        transaction_type = str(
            _enum_value(getattr(decoded, "type", None))
            or getattr(decoded, "rawType", None)
            or ""
        )
        if transaction_type != "Auto-Renewable Subscription":
            raise AppleVerificationError(
                "Apple transaction is not an auto-renewable subscription"
            )
        original_transaction_id = str(
            getattr(decoded, "originalTransactionId", "") or ""
        )
        transaction_id = str(getattr(decoded, "transactionId", "") or "")
        purchased_at = _milliseconds(getattr(decoded, "purchaseDate", None))
        expires_at = _milliseconds(getattr(decoded, "expiresDate", None))
        if not original_transaction_id or not transaction_id:
            raise AppleVerificationError("Apple transaction identity is missing")
        if purchased_at is None or expires_at is None:
            raise AppleVerificationError("Apple subscription period is missing")
        return VerifiedAppleTransaction(
            original_transaction_id=original_transaction_id,
            transaction_id=transaction_id,
            product_id=product_id,
            billing_interval=billing_interval,
            purchased_at=purchased_at,
            expires_at=expires_at,
            revoked_at=_milliseconds(getattr(decoded, "revocationDate", None)),
            signed_at=_milliseconds(getattr(decoded, "signedDate", None)),
        )

    def _verify_renewal(self, signed_renewal: str) -> VerifiedAppleRenewal:
        try:
            decoded = self.verifier.verify_and_decode_renewal_info(signed_renewal)
        except (VerificationException, ValueError, TypeError) as exc:
            raise AppleVerificationError("Apple renewal signature is invalid") from exc
        environment = str(
            _enum_value(getattr(decoded, "environment", None))
            or getattr(decoded, "rawEnvironment", None)
            or ""
        )
        if environment.lower() != self.environment:
            raise AppleVerificationError("Apple environment does not match")
        product_id = str(getattr(decoded, "productId", "") or "")
        auto_renew_product_id = str(
            getattr(decoded, "autoRenewProductId", "") or ""
        )
        for candidate in (product_id, auto_renew_product_id):
            if candidate and candidate not in self.product_intervals:
                raise AppleVerificationError("Unknown Apple subscription product")
        auto_renew_status = _enum_value(getattr(decoded, "autoRenewStatus", None))
        return VerifiedAppleRenewal(
            auto_renew_enabled=(
                bool(auto_renew_status) if auto_renew_status is not None else None
            ),
            billing_retry=bool(
                getattr(decoded, "isInBillingRetryPeriod", False)
            ),
            grace_period_expires_at=_milliseconds(
                getattr(decoded, "gracePeriodExpiresDate", None)
            ),
            signed_at=_milliseconds(getattr(decoded, "signedDate", None)),
        )

    def _validate_identity(self, bundle_id: Any, environment: Any) -> None:
        if str(bundle_id or "") != self.bundle_id:
            raise AppleVerificationError("Apple bundle ID does not match")
        environment_value = str(_enum_value(environment) or "").lower()
        if environment_value != self.environment:
            raise AppleVerificationError("Apple environment does not match")