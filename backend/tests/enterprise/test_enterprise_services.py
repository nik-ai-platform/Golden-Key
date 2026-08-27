from app.services.collaborative_research_service import CollaborativeResearchService
from app.services.data_license_service import DataLicenseService
from app.services.enterprise_ai_service import EnterpriseAIService
from app.services.enterprise_permission_service import EnterprisePermissionService
from app.services.enterprise_reporting_service import EnterpriseReportingService
from app.services.security_audit_service import SecurityAuditService
from app.services.subscription_service import SubscriptionService
from app.services.white_label_service import WhiteLabelService


def test_organizations_and_membership_permissions_work():
    permissions = EnterprisePermissionService()

    assert permissions.can_access("OWNER", "Anything") is True
    assert permissions.can_access("ANALYST", "Reports") is True
    assert permissions.can_access("VIEWER", "Models") is False


def test_workspaces_and_reports_are_generated():
    reporting = EnterpriseReportingService()

    report = reporting.generate("roi", {"research_activity": 243, "user_activity": 15})

    assert report["research_activity"] == 243
    assert len(reporting.list_reports()) >= 3


def test_api_keys_and_data_licensing_are_supported():
    license_service = DataLicenseService()
    white_label = WhiteLabelService()

    access = license_service.grant_access("Enterprise Client")
    branding = white_label.build_branding("Client Branding")

    assert "NBA Historical Database" in access["access"]
    assert branding["powered_by"] == "Golden Key"


def test_audit_logs_and_security_monitoring_work():
    security = SecurityAuditService()

    result = security.monitor({"suspicious_login": True, "data_access": "report_access"})

    assert result["status"] == "review"
    assert result["suspicious_login"] is True


def test_collaborative_research_and_subscription_features_work():
    research = CollaborativeResearchService()
    subscription = SubscriptionService()

    experiment = research.shared_experiment({"name": "ATS edge with rest advantage"})
    features = subscription.features_for("ENTERPRISE")

    assert experiment["status"] == "shared"
    assert "Unlimited Research" in features


def test_enterprise_ai_generates_executive_summary():
    ai = EnterpriseAIService()

    answer = ai.answer("Summarize today's NBA opportunities.")

    assert "Celtics ATS" in answer
