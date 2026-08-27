from app.schemas.dashboard import DashboardResponse
from app.schemas.team_intelligence import TeamIntelligenceSummary


def test_team_intelligence_summary_model_validates():
    summary = TeamIntelligenceSummary(
        team="Atlanta Dream",
        record="18-8",
        last10="8-2",
        offense=87.4,
        defense=79.2,
        momentum=91.5,
        strength=84.3,
    )

    assert summary.team == "Atlanta Dream"
    assert summary.record == "18-8"
    assert summary.last10 == "8-2"
    assert summary.offense == 87.4
    assert summary.defense == 79.2
    assert summary.momentum == 91.5
    assert summary.strength == 84.3


def test_dashboard_response_uses_simple_contract():
    response = DashboardResponse(
        system_health="healthy",
        overall_accuracy=72.5,
        total_predictions=1,
        recent_predictions=["p1"],
        top_teams=[],
        model_versions=[{"model": "NPI-v1", "accuracy": 72.5}],
    )

    assert response.model_dump() == {
        "system_health": "healthy",
        "overall_accuracy": 72.5,
        "total_predictions": 1,
        "recent_predictions": ["p1"],
        "top_teams": [],
        "model_versions": [{"model": "NPI-v1", "accuracy": 72.5}],
        "model_lab": None,
    }
