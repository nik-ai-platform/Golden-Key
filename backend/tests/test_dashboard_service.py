from app.services.dashboard_service import DashboardService


def test_get_dashboard_delegates_to_facade():
    expected = {
        "system_health": "healthy",
        "overall_accuracy": 72.5,
        "total_predictions": 2,
        "recent_predictions": ["p1", "p2"],
        "top_teams": [],
        "model_versions": [{"model": "NPI-v1", "accuracy": 72.5}],
    }

    class _FakeAnalyticsFacade:
        def __init__(self):
            self.calls = []

        def get_dashboard_data(self, db, team_id=None):
            self.calls.append((db, team_id))
            return expected

    fake_facade = _FakeAnalyticsFacade()
    service = DashboardService(analytics_facade=fake_facade)
    db = object()

    result = service.get_dashboard(db)

    assert fake_facade.calls == [(db, None)]
    assert result == expected


def test_get_dashboard_passes_team_id_to_facade():
    expected = {
        "system_health": "healthy",
        "overall_accuracy": 60.0,
        "total_predictions": 0,
        "recent_predictions": [],
        "top_teams": [
            {
                "team_id": 11,
                "team_name": "Atlanta Dream",
                "momentum": 80.0,
                "strength_rating": 84.3,
            }
        ],
        "model_versions": [{"model": "NPI-v2", "accuracy": 60.0}],
    }

    class _FakeAnalyticsFacade:
        def __init__(self):
            self.calls = []

        def get_dashboard_data(self, db, team_id=None):
            self.calls.append((db, team_id))
            return expected

    fake_facade = _FakeAnalyticsFacade()
    service = DashboardService(analytics_facade=fake_facade)
    db = object()

    result = service.get_dashboard(
        db,
        team_id=11,
    )

    assert fake_facade.calls == [(db, 11)]
    assert result == expected


def test_get_team_intelligence_summary_returns_compact_payload():

    expected = {
        "team": "Atlanta Dream",
        "record": "18-8",
        "last10": "8-2",
        "offense": 87.4,
        "defense": 79.2,
        "momentum": 91.5,
        "strength": 84.3,
    }

    class _FakeAnalyticsFacade:
        def __init__(self):
            self.calls = []

        def get_team_intelligence_summary(self, db, team_id):
            self.calls.append((db, team_id))
            return expected

    fake_facade = _FakeAnalyticsFacade()
    service = DashboardService(analytics_facade=fake_facade)
    db = object()

    result = service.get_team_intelligence_summary(db, 11)

    assert fake_facade.calls == [(db, 11)]
    assert result == expected


def test_get_dashboard_bundle_delegates_to_facade_bundle():
    expected = {
        "dashboard": {
            "system_health": "healthy",
            "overall_accuracy": 72.5,
            "total_predictions": 2,
            "recent_predictions": ["p1", "p2"],
            "top_teams": [],
            "model_versions": [{"model": "NPI-v1", "accuracy": 72.5}],
        },
        "trends": {
            "daily": ["daily"],
            "weekly": ["weekly"],
            "monthly": ["monthly"],
            "team": None,
            "sport": [],
            "model": [],
        },
    }

    class _FakeAnalyticsFacade:
        def __init__(self):
            self.calls = []

        def get_dashboard_bundle(self, db, team_id=None, sport=None, version=None):
            self.calls.append((db, team_id, sport, version))
            return expected

    fake_facade = _FakeAnalyticsFacade()
    service = DashboardService(analytics_facade=fake_facade)
    db = object()

    result = service.get_dashboard_bundle(db, team_id=11, sport="NBA", version="NPI-v1")

    assert fake_facade.calls == [(db, 11, "NBA", "NPI-v1")]
    assert result == expected
