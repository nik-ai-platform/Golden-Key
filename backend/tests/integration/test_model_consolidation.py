from app.services.model_consolidation_service import ModelConsolidationService
from app.services.system_health_service import SystemHealthService


def test_consolidation_service_exposes_deprecation_policy():
    service = ModelConsolidationService()
    items = service.list_deprecations()

    tables = {item["table_name"] for item in items}
    assert "prediction_results" in tables
    assert "prediction_evaluations" in tables
    assert "prediction_history" in tables
    assert "research_agent_jobs" in tables


def test_consolidation_service_flags_deprecated_tables():
    service = ModelConsolidationService()

    assert service.is_deprecated("prediction_results") is True
    assert service.is_deprecated("research_agent_jobs") is True
    assert service.is_deprecated("games") is False


def test_system_health_reports_consolidation_status_fields():
    health = SystemHealthService().check()

    assert "consolidation" in health
    assert "deprecated_tables" in health
    assert int(health["deprecated_tables"]) >= 0
