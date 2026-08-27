from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.role import ROLE_PERMISSIONS, Role
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.services.admin_service import AdminService
from app.services.api_gateway_service import ApiGatewayService
from app.services.billing_service import StripeBillingService
from app.services.feature_flag_service import FeatureFlagService
from app.services.permission_service import PermissionService
from app.services.product_analytics_service import ProductAnalyticsService


class DummyUser:
    def __init__(self, role: Role):
        self.role = role


def test_role_enforcement_and_limits():
    service = PermissionService()
    free_user = DummyUser(Role.FREE)
    premium_user = DummyUser(Role.PREMIUM)

    assert service.has_access(free_user, "basic_predictions") is True
    assert service.has_access(free_user, "premium_features") is False
    assert service.has_access(premium_user, "premium_features") is True
    assert service.enforce_limit(free_user) == 5
    assert service.enforce_limit(premium_user) == 10**9


def test_api_key_generation_and_validation():
    key = ApiKey.generate_key()
    hashed = ApiKey.hash_key(key)
    assert key.startswith("gk_live_")
    assert hashed


def test_gateway_and_feature_flags():
    gateway = ApiGatewayService()
    flags = FeatureFlagService()

    assert gateway.authenticate("secret") is True
    assert gateway.check_rate_limit("secret", 10) is True
    assert gateway.track_quota("secret", 100) is True
    assert flags.is_enabled("live_betting_ai") is True


def test_subscription_and_billing_flow():
    billing = StripeBillingService()
    subscription = Subscription(user_id=1, plan=SubscriptionPlan.PRO.value, status=SubscriptionStatus.ACTIVE.value)

    assert billing.create_checkout_session()["provider"] == "stripe"
    assert subscription.plan == SubscriptionPlan.PRO.value
    assert subscription.status == SubscriptionStatus.ACTIVE.value


def test_organization_permissions_and_admin_metrics():
    admin = AdminService()
    organization = Organization(name="Contoso", owner_id=1, plan="ENTERPRISE")
    audit = AuditLog(action="login", target="admin")

    assert organization.plan == "ENTERPRISE"
    assert admin.get_metrics()["enterprise"] == 27
    assert audit.action == "login"


def test_product_analytics_snapshot():
    analytics = ProductAnalyticsService()
    snapshot = analytics.snapshot()
    assert snapshot["revenue"] == 58400
    assert snapshot["daily_active_users"] > 0
