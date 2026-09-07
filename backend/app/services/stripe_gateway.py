from __future__ import annotations

from typing import Any

import stripe

from app.core.config import settings


class StripeSandboxConfigurationError(RuntimeError):
    pass


class StripeGateway:
    def __init__(self, secret_key: str, webhook_secret: str = ""):
        if not secret_key.startswith("sk_test_"):
            raise StripeSandboxConfigurationError(
                "Stripe sandbox requires an sk_test_ secret key"
            )
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret

    @classmethod
    def from_settings(cls, *, require_webhook_secret: bool = False) -> "StripeGateway":
        if not settings.STRIPE_TEST_MODE_ENABLED:
            raise StripeSandboxConfigurationError("Stripe sandbox is disabled")
        if require_webhook_secret and not settings.STRIPE_WEBHOOK_SECRET.startswith("whsec_"):
            raise StripeSandboxConfigurationError(
                "Stripe webhook secret is not configured"
            )
        return cls(settings.STRIPE_SECRET_KEY, settings.STRIPE_WEBHOOK_SECRET)

    def create_checkout_session(
        self,
        *,
        user_id: int,
        email: str,
        plan: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_id: str | None = None,
    ) -> Any:
        customer = {"customer": customer_id} if customer_id else {"customer_email": email}
        metadata = {
            "golden_key_user_id": str(user_id),
            "golden_key_plan": plan,
        }
        return stripe.checkout.Session.create(
            api_key=self.secret_key,
            mode="subscription",
            client_reference_id=str(user_id),
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            subscription_data={"metadata": metadata},
            **customer,
        )

    def create_billing_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
    ) -> Any:
        return stripe.billing_portal.Session.create(
            api_key=self.secret_key,
            customer=customer_id,
            return_url=return_url,
        )

    def construct_webhook_event(self, payload: bytes, signature: str | None) -> Any:
        return stripe.Webhook.construct_event(
            payload,
            signature,
            self.webhook_secret,
        )

    def retrieve_subscription(self, subscription_id: str) -> Any:
        return stripe.Subscription.retrieve(
            subscription_id,
            api_key=self.secret_key,
            expand=["items.data.price"],
        )