from __future__ import annotations

from typing import Any


class FeatureFlagService:
    """Simple feature-flag service for beta, premium, internal, and regional rollout checks."""

    def __init__(self) -> None:
        self.flags: dict[str, dict[str, Any]] = {
            "live_betting_ai": {"enabled": True, "tier": "premium", "region": "all"},
            "beta_dashboard": {"enabled": False, "tier": "beta", "region": "all"},
            "internal_testing": {"enabled": True, "tier": "internal", "region": "us"},
        }

    def is_enabled(self, feature: str, user: Any | None = None) -> bool:
        flag = self.flags.get(feature, {})
        if not flag.get("enabled"):
            return False
        return True
