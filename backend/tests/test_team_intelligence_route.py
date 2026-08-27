from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.core.roles import UserRole
from app.main import app


class _FakeHistoricalService:
    def get_recent_games(self, db, team_id, limit):
        return [
            SimpleNamespace(
                id=101,
                home_team_id=team_id,
                home_score=92,
                away_score=85,
                away_team_id=2,
            ),
            SimpleNamespace(
                id=102,
                home_team_id=2,
                home_score=84,
                away_score=89,
                away_team_id=team_id,
            ),
            SimpleNamespace(
                id=103,
                home_team_id=team_id,
                home_score=88,
                away_score=79,
                away_team_id=2,
            ),
        ]

    def build_team_profile(self, games, team_id):
        return {
            "recent_form": 82.5,
            "win_rate": 76.4,
            "trend": 76.4,
            "scoring_average": 84.1,
            "defense_average": 79.8,
        }

    def calculate_game_result(self, game, team_id):
        is_home = game.home_team_id == team_id
        points_for = game.home_score if is_home else game.away_score
        points_against = game.away_score if is_home else game.home_score

        return {
            "won": points_for > points_against,
            "points_for": points_for,
            "points_against": points_against,
        }

    def calculate_average(self, values):
        return round(sum(values) / len(values), 2) if values else 0

    def calculate_win_rate(self, wins, total_games):
        return round((wins / total_games) * 100, 2) if total_games else 0

    def calculate_trend(self, values):
        return 76.4


class _FakeTeamRepo:
    def get_team(self, db, team_id):
        return SimpleNamespace(
            id=team_id,
            name="Boston Celtics",
            performance=SimpleNamespace(
                offensive_rating=118.2,
                defensive_rating=109.7,
            ),
        )


class _FakePredictionRepo:
    def get_latest_snapshot_for_game(self, db, game_id):
        return SimpleNamespace(confidence=90.0, game_id=game_id)


class _FakeAnalyticsRepo:
    def get_by_game(self, db, game_id):
        return SimpleNamespace(
            implied_home_probability=0.842,
            implied_away_probability=0.679,
        )


class _EmptyHistoricalService:
    def get_recent_games(self, db, team_id, limit):
        return []

    def build_team_profile(self, games, team_id):
        return {
            "recent_form": 0,
            "win_rate": 0,
            "trend": 0,
            "scoring_average": 0,
            "defense_average": 0,
        }

    def calculate_game_result(self, game, team_id):
        return None

    def calculate_average(self, values):
        return 0

    def calculate_win_rate(self, wins, total_games):
        return 0

    def calculate_trend(self, values):
        return 0


def test_get_team_intelligence_route_returns_canonical_payload(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import teams as teams_router
    from app.services.team_intelligence_service import TeamIntelligenceService

    app.dependency_overrides[teams_router.get_db] = _override_get_db
    app.dependency_overrides[require_viewer] = lambda: AuthUser(
        id=1,
        username="viewer",
        email="viewer@example.com",
        role=UserRole.VIEWER,
        is_active=True,
    )

    service = TeamIntelligenceService(
        historical_service=_FakeHistoricalService(),
        team_repo=_FakeTeamRepo(),
        prediction_repo=_FakePredictionRepo(),
        analytics_repo=_FakeAnalyticsRepo(),
    )

    monkeypatch.setattr(teams_router, "TeamIntelligenceService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/teams/3/intelligence")

    assert response.status_code == 200
    assert response.json() == {
        "team_id": 3,
        "team_name": "Boston Celtics",
        "momentum": 30.0,
        "consistency": 8.63,
        "trend": "up",
        "home_win_pct": 100.0,
        "away_win_pct": 100.0,
        "average_margin": 7.0,
        "offensive_rating": 118.2,
        "defensive_rating": 109.7,
        "strength_rating": 76.4,
    }

    app.dependency_overrides.clear()


def test_get_team_intelligence_route_handles_empty_history(monkeypatch):
    fake_db = object()

    def _override_get_db():
        yield fake_db

    from app.api.v1 import teams as teams_router
    from app.services.team_intelligence_service import TeamIntelligenceService

    app.dependency_overrides[teams_router.get_db] = _override_get_db
    app.dependency_overrides[require_viewer] = lambda: AuthUser(
        id=1,
        username="viewer",
        email="viewer@example.com",
        role=UserRole.VIEWER,
        is_active=True,
    )

    service = TeamIntelligenceService(
        historical_service=_EmptyHistoricalService(),
        team_repo=_FakeTeamRepo(),
        prediction_repo=_FakePredictionRepo(),
        analytics_repo=_FakeAnalyticsRepo(),
    )

    monkeypatch.setattr(teams_router, "TeamIntelligenceService", lambda: service)

    client = TestClient(app)
    response = client.get("/api/v1/teams/999999/intelligence")

    assert response.status_code == 200
    assert response.json() == {
        "team_id": 999999,
        "team_name": "Boston Celtics",
        "momentum": 0.0,
        "consistency": 0.0,
        "trend": "down",
        "home_win_pct": 0.0,
        "away_win_pct": 0.0,
        "average_margin": 0.0,
        "offensive_rating": 118.2,
        "defensive_rating": 109.7,
        "strength_rating": 0.0,
    }

    app.dependency_overrides.clear()