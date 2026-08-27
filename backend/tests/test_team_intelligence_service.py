from types import SimpleNamespace

from app.services.team_intelligence_service import TeamIntelligenceService


class _FakeHistoricalService:
    def __init__(self, games=None, profile=None):
        self.games = games or []
        self.profile = profile or {}
        self.calls = []

    def get_recent_games(self, db, team_id, limit):
        self.calls.append(("get_recent_games", db, team_id, limit))
        return self.games

    def build_team_profile(self, games, team_id):
        self.calls.append(("build_team_profile", games, team_id))
        return self.profile

    def calculate_game_result(self, game, team_id):
        self.calls.append(("calculate_game_result", game.id, team_id))
        return {
            "won": game.won,
            "points_for": game.points_for,
            "points_against": game.points_against,
        }

    def calculate_average(self, values):
        self.calls.append(("calculate_average", values))
        return round(sum(values) / len(values), 2) if values else 0

    def calculate_win_rate(self, wins, total_games):
        self.calls.append(("calculate_win_rate", wins, total_games))
        return round((wins / total_games) * 100, 2) if total_games else 0

    def calculate_trend(self, values):
        self.calls.append(("calculate_trend", values))
        return 76.4


class _FakeTeamRepo:
    def __init__(self, team):
        self.team = team
        self.calls = []

    def get_team(self, db, team_id):
        self.calls.append((db, team_id))
        return self.team


class _FakePredictionRepo:
    def __init__(self, snapshot=None):
        self.snapshot = snapshot
        self.calls = []

    def get_latest_snapshot_for_game(self, db, game_id):
        self.calls.append((db, game_id))
        return self.snapshot


class _FakeAnalyticsRepo:
    def __init__(self, analytics=None):
        self.analytics = analytics
        self.calls = []

    def get_by_game(self, db, game_id):
        self.calls.append((db, game_id))
        return self.analytics


class _Game:
    def __init__(self, game_id, won, points_for, points_against, home_team_id):
        self.id = game_id
        self.won = won
        self.points_for = points_for
        self.points_against = points_against
        self.home_team_id = home_team_id


def test_build_team_intelligence_combines_existing_components():
    team = SimpleNamespace(
        id=1,
        name="Atlanta Dream",
        performance=SimpleNamespace(
            offensive_rating=88.2,
            defensive_rating=81.3,
        ),
    )

    historical_profile = {
        "recent_form": 82.5,
        "win_rate": 76.4,
        "trend": 76.4,
        "scoring_average": 84.1,
        "defense_average": 79.8,
    }

    snapshot = SimpleNamespace(confidence=90.0)
    analytics = SimpleNamespace(implied_home_probability=0.61)

    service = TeamIntelligenceService()

    result = service.build_team_intelligence(
        team,
        historical_profile,
        record_summary={
            "home_record": "14-4",
            "away_record": "10-7",
            "last10": "8-2",
            "average_margin": 7.6,
            "home_win_pct": 100.0,
            "away_win_pct": 100.0,
            "consistency": 100.0,
        },
        prediction_snapshot=snapshot,
        analytics=analytics,
    )

    assert result.model_dump() == {
        "team_id": 1,
        "team_name": "Atlanta Dream",
        "momentum": 80.0,
        "consistency": 100.0,
        "trend": "up",
        "home_win_pct": 100.0,
        "away_win_pct": 100.0,
        "average_margin": 7.6,
        "offensive_rating": 88.2,
        "defensive_rating": 81.3,
        "strength_rating": 76.4,
    }


def test_calculate_momentum_uses_last_10_wins():
    service = TeamIntelligenceService()

    assert service._calculate_momentum({
        "results": [
            {"won": True},
            {"won": True},
            {"won": True},
            {"won": True},
            {"won": True},
            {"won": True},
            {"won": True},
            {"won": True},
            {"won": False},
            {"won": False},
        ]
    }) == 80.0


def test_calculate_trend_labels_direction_from_score():
    service = TeamIntelligenceService()

    trend_value, trend_label = service._calculate_trend(
        {"strength": 76.4},
        {"trend": 50.0},
    )

    assert trend_value == 76.4
    assert trend_label == "up"


def test_home_and_away_percentages_are_preserved():
    team = SimpleNamespace(id=1, name="Atlanta Dream")
    service = TeamIntelligenceService()

    result = service.build_team_intelligence(
        team,
        {"trend": 76.4, "scoring_average": 84.1, "defense_average": 79.8},
        record_summary={
            "home_record": "8-2",
            "away_record": "4-6",
            "home_win_pct": 80.0,
            "away_win_pct": 40.0,
            "results": [
                {"won": True, "points_for": 110, "points_against": 100},
                {"won": True, "points_for": 108, "points_against": 99},
                {"won": False, "points_for": 95, "points_against": 101},
            ],
        },
    )

    assert result.home_win_pct == 80.0
    assert result.away_win_pct == 40.0


def test_empty_team_history_returns_zeroed_profile():
    db = object()

    team = SimpleNamespace(
        id=999999,
        name="Empty History Team",
        performance=None,
    )

    historical_service = _FakeHistoricalService(
        games=[],
        profile={
            "recent_form": 0,
            "win_rate": 0,
            "trend": 0,
            "scoring_average": 0,
            "defense_average": 0,
        },
    )
    team_repo = _FakeTeamRepo(team)
    prediction_repo = _FakePredictionRepo(None)
    analytics_repo = _FakeAnalyticsRepo(None)

    service = TeamIntelligenceService(
        historical_service=historical_service,
        team_repo=team_repo,
        prediction_repo=prediction_repo,
        analytics_repo=analytics_repo,
    )

    profile = service.build_profile(db, 999999)

    assert profile.team_id == 999999
    assert profile.momentum == 0
    assert profile.consistency == 0
    assert profile.home_win_pct == 0
    assert profile.away_win_pct == 0
    assert profile.average_margin == 0


def test_get_team_intelligence_assembles_existing_sources():
    db = object()

    games = [
        _Game(101, True, 92, 85, 1),
        _Game(102, False, 84, 89, 2),
        _Game(103, True, 88, 79, 1),
    ]

    team = SimpleNamespace(
        name="Atlanta Dream",
        performance=SimpleNamespace(
            offensive_rating=88.2,
            defensive_rating=81.3,
        ),
    )

    historical_profile = {
        "recent_form": 82.5,
        "win_rate": 76.4,
        "trend": 76.4,
        "scoring_average": 84.1,
        "defense_average": 79.8,
    }

    snapshot = SimpleNamespace(confidence=90.0, game_id=103)
    analytics = SimpleNamespace(implied_home_probability=0.61)

    historical_service = _FakeHistoricalService(
        games=games,
        profile=historical_profile,
    )
    team_repo = _FakeTeamRepo(team)
    prediction_repo = _FakePredictionRepo(snapshot)
    analytics_repo = _FakeAnalyticsRepo(analytics)

    service = TeamIntelligenceService(
        historical_service=historical_service,
        team_repo=team_repo,
        prediction_repo=prediction_repo,
        analytics_repo=analytics_repo,
    )

    result = service.get_team_intelligence(db, 1)

    assert team_repo.calls == [(db, 1)]
    assert prediction_repo.calls == [(db, 101)]
    assert analytics_repo.calls == [(db, 101)]
    assert result["momentum"] == 20.0
    assert result["consistency"] == 9.85
    assert result["trend"] == "up"
    assert result["offensive_rating"] == 88.2
    assert result["defensive_rating"] == 81.3
    assert result["home_record"] == "2-0"
    assert result["away_record"] == "0-1"
    assert result["last10"] == "2-1"
    assert result["average_margin"] == 3.67
