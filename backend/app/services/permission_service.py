from __future__ import annotations

from typing import Any

from app.models.role import ROLE_PERMISSIONS, Role


class PermissionService:
    """Determine feature access and usage limits for a user."""

    def has_access(self, user: Any, feature: str) -> bool:
        role = getattr(user, "role", None) or Role.FREE
        if isinstance(role, str):
            role = Role(role)
        permissions = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.FREE])
        if permissions.get("all"):
            return True
        return bool(permissions.get(feature))

    def enforce_limit(self, user: Any) -> int:
        role = getattr(user, "role", None) or Role.FREE
        if isinstance(role, str):
            role = Role(role)
        permissions = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS[Role.FREE])
        if permissions.get("unlimited_predictions"):
            return 10**9
        return int(permissions.get("daily_prediction_limit", 5))
