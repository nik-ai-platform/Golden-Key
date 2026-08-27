from types import SimpleNamespace

from app.services.analytics_facade import AnalyticsFacade


def test_get_historical_trends_delegates_to_trend_service():
    class _FakeTrendService:
        def __init__(self):
            self.calls = []

        def daily_trends(self, db):
            self.calls.append(("daily", db))
            return ["daily"]

        def weekly_trends(self, db):
            self.calls.append(("weekly", db))
            return ["weekly"]

        def monthly_trends(self, db):
            self.calls.append(("monthly", db))
            return ["monthly"]

        def team_trends(self, db, team_id):
            self.calls.append(("team", db, team_id))
            return SimpleNamespace(team="Atlanta Dream", last30=SimpleNamespace(accuracy=74.2, momentum=86.4))

        def sport_trends(self, db, sport):
            self.calls.append(("sport", db, sport))
            return [SimpleNamespace(sport="NBA", accuracy=72.8)]

        def model_trends(self, db, version):
            self.calls.append(("model", db, version))
            return [SimpleNamespace(version="NPI-v1", accuracy=68.2)]

    fake_trends = _FakeTrendService()
    facade = AnalyticsFacade(historical_trend_service=fake_trends)
    db = object()

    result = facade.get_historical_trends(db, team_id=11, sport="NBA", version="NPI-v1")

    assert fake_trends.calls == [
        ("daily", db),
        ("weekly", db),
        ("monthly", db),
        ("team", db, 11),
        ("sport", db, "NBA"),
        ("model", db, "NPI-v1"),
    ]
    assert result["daily"] == ["daily"]
    assert result["weekly"] == ["weekly"]
    assert result["monthly"] == ["monthly"]
    assert result["team"].team == "Atlanta Dream"
    assert result["sport"][0].sport == "NBA"
    assert result["model"][0].version == "NPI-v1"


def test_get_dashboard_bundle_combines_summary_and_trends():
    class _FakeFacadeDependencies:
        def __init__(self):
            self.dashboard_calls = []
            self.trend_calls = []

        def dashboard_statistics(self, db):
            self.dashboard_calls.append(db)
            return {
                "recent_predictions": ["p1"],
            }

    class _FakeAnalyticsService:
        def __init__(self):
            self.calls = []

        def dashboard_statistics(self, db):
            self.calls.append(db)
            return {
                "recent_predictions": ["p1"],
            }

    class _FakePredictionMetricsService:
        def overall_accuracy(self, db):
            return 72.5

        def accuracy_by_model_version(self, db):
            return {"NPI-v1": {"accuracy": 72.5}}

    class _FakeTeamIntelligenceService:
        def build_profile(self, db, team_id):
            return SimpleNamespace(
                team_id=team_id,
                team_name="Atlanta Dream",
                momentum=80.0,
                strength_rating=84.3,
            )

        def get_dashboard_summary(self, db, team_id):
            return {
                "team": "Atlanta Dream",
                "record": "18-8",
                "last10": "8-2",
                "offense": 87.4,
                "defense": 79.2,
                "momentum": 91.5,
                "strength": 84.3,
            }

    class _FakeTrendService:
        def daily_trends(self, db):
            return ["daily"]

        def weekly_trends(self, db):
            return ["weekly"]

        def monthly_trends(self, db):
            return ["monthly"]

        def team_trends(self, db, team_id):
            return {"team": "Atlanta Dream", "last30": {"accuracy": 74.2, "momentum": 86.4}}

        def sport_trends(self, db, sport):
            return ["sport"]

        def model_trends(self, db, version):
            return ["model"]

    facade = AnalyticsFacade(
        analytics_service=_FakeAnalyticsService(),
        team_intelligence_service=_FakeTeamIntelligenceService(),
        prediction_metrics_service=_FakePredictionMetricsService(),
        historical_trend_service=_FakeTrendService(),
    )
    db = object()

    bundle = facade.get_dashboard_bundle(db, team_id=11, sport="NBA", version="NPI-v1")

    assert bundle["dashboard"]["recent_predictions"] == ["p1"]
    assert bundle["trends"] == {
        "daily": ["daily"],
        "weekly": ["weekly"],
        "monthly": ["monthly"],
        "team": {"team": "Atlanta Dream", "last30": {"accuracy": 74.2, "momentum": 86.4}},
        "sport": ["sport"],
        "model": ["model"],
    }
