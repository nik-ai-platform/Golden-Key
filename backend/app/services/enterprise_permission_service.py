from __future__ import annotations


class EnterprisePermissionService:
    ROLE_PERMISSIONS = {
        "OWNER": {"Everything"},
        "ADMIN": {"Models", "Reports", "Research", "Users", "API Usage"},
        "ANALYST": {"Models", "Reports", "Research"},
        "RESEARCHER": {"Research", "Reports"},
        "VIEWER": {"Dashboards only"},
        "API_USER": {"API Usage"},
    }

    def can_access(self, role: str, capability: str) -> bool:
        normalized_role = (role or "VIEWER").upper()
        permissions = self.ROLE_PERMISSIONS.get(normalized_role, set())
        return "Everything" in permissions or capability in permissions or normalized_role == "OWNER"

    def permissions_for(self, role: str) -> list[str]:
        normalized_role = (role or "VIEWER").upper()
        return sorted(self.ROLE_PERMISSIONS.get(normalized_role, {"Dashboards only"}))
