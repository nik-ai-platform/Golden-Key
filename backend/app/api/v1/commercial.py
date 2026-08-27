from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.models.api_key import ApiKey
from app.models.organization import Organization
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.schemas.commercial import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    BillingWebhookRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    PermissionCheckResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
)
from app.services.admin_service import AdminService
from app.services.api_gateway_service import ApiGatewayService
from app.services.billing_service import StripeBillingService
from app.services.feature_flag_service import FeatureFlagService
from app.services.permission_service import PermissionService
from app.services.product_analytics_service import ProductAnalyticsService

router = APIRouter(prefix="/commercial", tags=["Commercial"], dependencies=[Depends(require_admin)])

permission_service = PermissionService()
billing_service = StripeBillingService()
api_gateway_service = ApiGatewayService()
feature_flag_service = FeatureFlagService()
admin_service = AdminService()
product_analytics_service = ProductAnalyticsService()

SUBSCRIPTIONS: list[SubscriptionResponse] = []
API_KEYS: list[ApiKeyResponse] = []
ORGANIZATIONS: list[OrganizationResponse] = []


class DummyUser:
    def __init__(self, role: str):
        self.role = role


@router.post("/subscriptions", response_model=SubscriptionResponse)
def create_subscription(payload: SubscriptionCreateRequest | None = None, plan: str | None = None, user_id: int = 1):
    if payload is None:
        payload = SubscriptionCreateRequest(plan=plan or "FREE", user_id=user_id)
    subscription = Subscription(user_id=payload.user_id, plan=payload.plan.lower(), active=True)
    response = SubscriptionResponse(user_id=subscription.user_id, plan=subscription.plan.upper(), status=SubscriptionStatus.ACTIVE.value)
    SUBSCRIPTIONS.append(response)
    return response


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def list_subscriptions():
    return SUBSCRIPTIONS or [{"user_id": 1, "plan": SubscriptionPlan.PRO.value, "status": SubscriptionStatus.ACTIVE.value}]


@router.post("/billing/webhook")
def billing_webhook(payload: BillingWebhookRequest | None = None, provider: str | None = None, event_type: str | None = None):
    if payload is None:
        payload = BillingWebhookRequest(provider=provider or "stripe", event_type=event_type or "checkout.completed")
    return {"provider": payload.provider, "event_type": payload.event_type, **billing_service.sync_subscription()}


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(payload: ApiKeyCreateRequest | None = None, owner: int = 1, quota: int = 1000):
    if payload is None:
        payload = ApiKeyCreateRequest(owner=owner, quota=quota)
    key = ApiKey.generate_key()
    api_key = ApiKey(key=key, owner=payload.owner, quota=payload.quota)
    response = ApiKeyResponse(key=api_key.key, owner=api_key.owner, quota=api_key.quota)
    API_KEYS.append(response)
    return response


@router.get("/admin/users")
def admin_users():
    return admin_service.list_users()


@router.get("/admin/metrics")
def admin_metrics():
    return admin_service.get_metrics()


@router.get("/admin/audit")
def admin_audit():
    return admin_service.get_audit_entries()


@router.get("/admin/feature-flags")
def feature_flags():
    return {"live_betting_ai": feature_flag_service.is_enabled("live_betting_ai")}


@router.get("/admin/analytics")
def product_analytics():
    return product_analytics_service.snapshot()


@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(payload: OrganizationCreateRequest):
    org = Organization(name=payload.name, owner_id=payload.owner_id)
    response = OrganizationResponse(id=org.id, name=org.name, owner_id=org.owner_id, plan=org.plan or "FREE")
    ORGANIZATIONS.append(response)
    return response


@router.get("/permissions/{feature}", response_model=PermissionCheckResponse)
def check_permission(feature: str, role: str = "FREE"):
    user = DummyUser(role=role)
    allowed = permission_service.has_access(user, feature)
    return PermissionCheckResponse(feature=feature, allowed=allowed)


@router.get("/gateway/health")
def gateway_health():
    return {"status": api_gateway_service.version()}
