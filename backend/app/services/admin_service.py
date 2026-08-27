from __future__ import annotations

from typing import Any


class AdminService:
    """Administrative operations for users, subscriptions, billing, infrastructure, and audits."""

    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "users": 4821,
            "premium": 1243,
            "enterprise": 27,
            "predictions_today": 118000,
            "mrr": 58400,
            "api_requests": 3400000,
            "infrastructure": "healthy",
        }

    def list_users(self) -> list[dict[str, Any]]:
        return [{"id": 1, "email": "admin@example.com"}]

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics

    def get_audit_entries(self) -> list[dict[str, Any]]:
        return [{"action": "login", "user_id": 1}]
