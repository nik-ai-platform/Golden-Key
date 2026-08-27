from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.workspace import Workspace
from app.services.collaborative_research_service import CollaborativeResearchService
from app.services.enterprise_ai_service import EnterpriseAIService
from app.services.enterprise_permission_service import EnterprisePermissionService
from app.services.enterprise_reporting_service import EnterpriseReportingService
from app.services.security_audit_service import SecurityAuditService
from app.services.subscription_service import SubscriptionService
from app.services.white_label_service import WhiteLabelService
from app.services.data_license_service import DataLicenseService

router = APIRouter(tags=["Enterprise"], dependencies=[Depends(require_admin)])

permission_service = EnterprisePermissionService()
reporting_service = EnterpriseReportingService()
research_service = CollaborativeResearchService()
security_service = SecurityAuditService()
enterprise_ai_service = EnterpriseAIService()
subscription_service = SubscriptionService()

ORGANIZATIONS: list[dict] = []
WORKSPACES: list[dict] = []
MEMBERS: list[dict] = []
REPORTS: list[dict] = []
API_KEYS: list[dict] = []
AUDIT_ENTRIES: list[dict] = []


@router.post("/organizations")
def create_organization(payload: dict):
    org = Organization(
        name=payload.get("name", "Elite Sports Analytics"),
        organization_type=payload.get("organization_type", "Sports Analytics Firm"),
        subscription_plan=payload.get("subscription_plan", "ENTERPRISE"),
    )
    record = {
        "id": len(ORGANIZATIONS) + 1,
        "name": org.name,
        "organization_type": org.organization_type,
        "subscription_plan": org.subscription_plan,
        "created_at": str(org.created_at),
        "updated_at": str(org.updated_at),
    }
    ORGANIZATIONS.append(record)
    return record


@router.get("/workspaces")
def list_workspaces():
    if not WORKSPACES:
        workspace = Workspace(organization_id=1, name="Golden Key NBA Research Lab", settings='{"members": 15, "active_projects": 42}')
        WORKSPACES.append({"id": 1, "organization_id": workspace.organization_id, "name": workspace.name, "settings": workspace.settings, "created_at": str(workspace.created_at)})
    return WORKSPACES


@router.post("/members")
def create_member(payload: dict):
    member = OrganizationMember(
        organization_id=payload.get("organization_id", 1),
        user_id=payload.get("user_id", 1),
        role=payload.get("role", "researcher"),
        permissions=str(payload.get("permissions", ["view_models", "create_reports"])),
    )
    record = {"id": len(MEMBERS) + 1, "organization_id": member.organization_id, "user_id": member.user_id, "role": member.role, "permissions": member.permissions, "joined_at": str(member.joined_at)}
    MEMBERS.append(record)
    return record


@router.get("/reports")
def get_reports(report_type: str = "enterprise"):
    report = reporting_service.generate(report_type, {"research_activity": 243, "user_activity": 15, "roi_reports": "+12.4%"})
    REPORTS.append(report)
    return REPORTS or [report]


@router.post("/api-keys")
def create_api_key(payload: dict):
    key = ApiKey.generate_key()
    api_key = ApiKey(
        organization_id=payload.get("organization_id", 1),
        key=key,
        key_hash=ApiKey.hash_key(key),
        permissions=str(payload.get("permissions", ["view_models", "create_reports"])),
        rate_limit=payload.get("rate_limit", 60),
        expires_at=payload.get("expires_at"),
    )
    record = {
        "id": len(API_KEYS) + 1,
        "organization_id": api_key.organization_id,
        "key_hash": api_key.key_hash,
        "permissions": api_key.permissions,
        "rate_limit": api_key.rate_limit,
        "created_at": str(api_key.created_at),
        "expires_at": str(api_key.expires_at) if api_key.expires_at else None,
    }
    API_KEYS.append(record)
    return record


@router.get("/audit")
def get_audit():
    entry = AuditLog(action="Modified Research Model", actor_id=1, target="research", details="Enterprise audit ready")
    monitored = security_service.monitor({"data_access": "report_access"})
    record = {"user": "Analyst01", "action": entry.action, "time": "2026-08-05", "status": monitored["status"]}
    AUDIT_ENTRIES.append(record)
    return AUDIT_ENTRIES or [record]


@router.get("/enterprise/overview")
def enterprise_overview(role: str = "ANALYST"):
    ai = enterprise_ai_service.summarize_opportunities("Summarize today\'s NBA opportunities")
    return {
        "organization": "Elite Sports Analytics",
        "active_models": 18,
        "research_projects": 243,
        "api_calls": "2.4M",
        "permissions": permission_service.permissions_for(role),
        "subscription_features": subscription_service.features_for("ENTERPRISE"),
        "ai_summary": ai,
        "research": research_service.shared_experiment({"name": "ATS edge with rest advantage"}),
        "white_label": WhiteLabelService().build_branding("Elite Sports Analytics"),
        "data_license": DataLicenseService().grant_access("Enterprise Client"),
    }
