from datetime import datetime, timedelta

from app.services import historical_trend_service as trend_module
from app.services.historical_trend_service import HistoricalTrendService


def _row(game_date, correct, confidence, home=1, away=2, sport="NBA", model="v1"):
    return (game_date, correct, confidence, home, away, sport, model)


def test_daily_weekly_monthly_accuracy_aggregate_predictions_correct_and_accuracy(monkeypatch):
    rows = [
        _row(datetime(2026, 1, 1), True, 80.0),
        _row(datetime(2026, 1, 1), False, 60.0),
        _row(datetime(2026, 1, 9), True, 90.0),
    ]

    monkeypatch.setattr(
        trend_module.analytics_repository,
        "get_evaluation_trend_rows",
        lambda db, team_id=None, sport=None, version=None: rows,
    )

    service = HistoricalTrendService()
    db = object()

    daily = service.daily_trends(db)
    weekly = service.weekly_trends(db)
    monthly = service.monthly_trends(db)

    assert daily[0].period == "2026-01-01"
    assert daily[0].predictions == 2
    assert daily[0].accuracy == 50.0
    assert daily[0].confidence == 70.0
    assert daily[0].correct == 1

    assert len(weekly) == 2
    assert weekly[0].predictions == 2
    assert weekly[1].predictions == 1
    assert weekly[0].correct == 1

    assert len(monthly) == 1
    assert monthly[0].predictions == 3
    assert monthly[0].accuracy == 66.67
    assert monthly[0].correct == 2


def test_team_trends_return_last30_summary(monkeypatch):
    now = datetime(2026, 1, 31)
    rows = [
        _row(now - timedelta(days=10), True, 90.0, home=11, away=22),
        _row(now - timedelta(days=5), True, 80.0, home=22, away=11),
        _row(now - timedelta(days=40), False, 70.0, home=11, away=33),
    ]

    class _FakeTeamRepo:
        def get_team(self, db, team_id):
            return type("Team", (), {"name": "Atlanta Dream"})()

    def _fake_rows(db, team_id=None, sport=None, version=None):
        return rows if team_id == 11 else []

    monkeypatch.setattr(
        trend_module.analytics_repository,
        "get_evaluation_trend_rows",
        _fake_rows,
    )

    service = HistoricalTrendService(team_repo=_FakeTeamRepo())
    db = object()

    team = service.team_trends(db, 11)

    assert team.team == "Atlanta Dream"
    assert team.last30.accuracy == 100.0
    assert team.last30.momentum == 85.0


def test_sport_trends_rank_sports_by_accuracy(monkeypatch):
    rows = [
        _row(datetime(2026, 1, 1), True, 80.0, sport="NBA", model="v1"),
        _row(datetime(2026, 1, 2), False, 70.0, sport="NBA", model="v1"),
        _row(datetime(2026, 1, 3), True, 90.0, sport="WNBA", model="v1"),
    ]

    monkeypatch.setattr(
        trend_module.analytics_repository,
        "get_evaluation_trend_rows",
        lambda db, team_id=None, sport=None, version=None: rows if sport is None else [row for row in rows if row[5] == sport],
    )

    service = HistoricalTrendService()

    result = service.sport_trends(object())

    assert [item.sport for item in result] == ["NBA", "WNBA"]
    assert [item.accuracy for item in result] == [50.0, 100.0]


def test_model_trends_rank_versions_by_accuracy(monkeypatch):
    rows = [
        _row(datetime(2026, 1, 1), True, 80.0, model="NPI-v1"),
        _row(datetime(2026, 1, 2), False, 70.0, model="NPI-v1"),
        _row(datetime(2026, 1, 3), True, 90.0, model="NPI-v2"),
    ]

    monkeypatch.setattr(
        trend_module.analytics_repository,
        "get_evaluation_trend_rows",
        lambda db, team_id=None, sport=None, version=None: rows if version is None else [row for row in rows if row[6] == version],
    )

    service = HistoricalTrendService()

    result = service.model_trends(object())

    assert [item.version for item in result] == ["NPI-v1", "NPI-v2"]
    assert [item.accuracy for item in result] == [50.0, 100.0]
