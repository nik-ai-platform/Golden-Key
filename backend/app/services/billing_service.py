from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BillingService(ABC):
    """Abstract billing integration that can be swapped between providers."""

    def create_checkout_session(self) -> dict[str, Any]:
        raise NotImplementedError

    def cancel_subscription(self) -> dict[str, Any]:
        raise NotImplementedError

    def sync_subscription(self) -> dict[str, Any]:
        raise NotImplementedError


class StripeBillingService(BillingService):
    """Stripe-backed implementation for subscriptions, trials, coupons, and invoices."""

    def create_checkout_session(self) -> dict[str, Any]:
        return {"provider": "stripe", "mode": "checkout"}

    def cancel_subscription(self) -> dict[str, Any]:
        return {"provider": "stripe", "status": "canceled"}

    def sync_subscription(self) -> dict[str, Any]:
        return {"provider": "stripe", "status": "synced"}
