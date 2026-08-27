from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    PREMIUM = "PREMIUM"
    PRO = "PRO"
    FREE = "FREE"
    API_CLIENT = "API_CLIENT"
    ENTERPRISE = "ENTERPRISE"


ROLE_PERMISSIONS = {
    Role.ADMIN: {"all": True},
    Role.STAFF: {"view_admin": True, "manage_users": True},
    Role.PREMIUM: {"premium_features": True, "unlimited_predictions": True},
    Role.PRO: {"pro_features": True, "unlimited_predictions": True, "api_access": True},
    Role.FREE: {"basic_predictions": True, "daily_prediction_limit": 5},
    Role.API_CLIENT: {"api_access": True, "rate_limited_api": True},
    Role.ENTERPRISE: {"enterprise_features": True, "unlimited_predictions": True, "api_access": True, "priority_support": True},
}
