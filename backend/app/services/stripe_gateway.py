from __future__ import annotations

from typing import Any

import stripe

from app.core.config import settings


class StripeSandboxConfigurationError(RuntimeError):
    pass


class StripeGateway:
    def __init__(self, secret_key: str, webhook_secret: str = ""):
        if not secret_key.startswith(("sk_test_", "rk_test_")):
            raise StripeSandboxConfigurationError(
                "Stripe sandbox requires an sk_test_ or rk_test_ secret key"
            )
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self.client = stripe.StripeClient(secret_key)

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
        return self.client.v1.checkout.sessions.create(
            params={
                "mode": "subscription",
                "client_reference_id": str(user_id),
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata,
                "subscription_data": {
                    "metadata": metadata,
                    "trial_period_days": 7,
                },
                **customer,
            }
        )

    def create_billing_portal_session(
        self,
        *,
        customer_id: str,
        return_url: str,
    ) -> Any:
        return self.client.v1.billing_portal.sessions.create(
            params={
                "customer": customer_id,
                "return_url": return_url,
            }
        )

    def construct_webhook_event(self, payload: bytes, signature: str | None) -> Any:
        return stripe.Webhook.construct_event(
            payload,
            signature,
            self.webhook_secret,
        )

    def retrieve_subscription(self, subscription_id: str) -> Any:
        return self.client.v1.subscriptions.retrieve(
            subscription_id,
            params={"expand": ["items.data.price"]},
        )