from app.services.ai_analyst_service import AIAnalystService
from app.services.analyst_context_service import AnalystContextService
from app.services.daily_report_service import DailyReportService


def test_context_builder_gathers_correct_data():
    service = AnalystContextService()
    context = service.build_context(7, {"game": "DAL vs PHX", "prediction": "DAL", "confidence": 84, "edge": 6.2, "risk": "LOW"})

    assert context["game"] == "DAL vs PHX"
    assert context["prediction"] == "DAL"
    assert context["confidence"] == 84


def test_missing_analytics_handled_safely():
    service = AnalystContextService()
    context = service.build_context(None)

    assert context["prediction"] == "No prediction"
    assert context["confidence"] == 0


def test_explanations_match_model_output():
    service = AIAnalystService()
    result = service.explain_prediction({"prediction": "DAL", "confidence": 84, "edge": 6.2})

    assert "DAL" in result["message"]
    assert result["language"] == "Model strongly favors"


def test_risk_language_matches_score():
    service = AIAnalystService()
    result = service.explain_risk({"risk_score": 42, "risk_level": "MEDIUM"})

    assert result["language"] == "Moderate risk"


def test_reports_generate_consistently():
    service = DailyReportService()
    report = service.generate_report()

    assert report["title"] == "Golden Key Daily Report"
    assert len(report["top_opportunities"]) == 2


def test_analyst_never_changes_predictions():
    service = AIAnalystService()
    context = {"prediction": "DAL"}
    response = service.answer_question("Why does Golden Key like this game?", context)

    assert "DAL" in response["answer"]
