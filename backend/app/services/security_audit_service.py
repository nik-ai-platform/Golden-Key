from __future__ import annotations


class SecurityAuditService:
    def monitor(self, event: dict | None) -> dict:
        event = event or {}
        return {
            "suspicious_login": event.get("suspicious_login", False),
            "permission_abuse": event.get("permission_abuse", False),
            "api_abuse": event.get("api_abuse", False),
            "data_access": event.get("data_access", "normal"),
            "status": "review" if any([event.get("suspicious_login"), event.get("permission_abuse"), event.get("api_abuse")]) else "clear",
        }
