from types import SimpleNamespace

from app.services.prediction_service import PredictionService


class _FakeDB:
    def __init__(self):
        self.added = []
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        if self.added:
            self.added[-1].id = 99

    def commit(self):
        return None

    def refresh(self, obj):
        self.refreshed.append(obj)


class _FakeValidationService:
    def validate_game(self, game):
        return True


class _FakeFeatureService:
    def calculate_team_features(self, performance):
        return {
            "offense": 70.0,
            "defense": 60.0,
            "form": 68.0,
            "rest_days": 1.0,
        }

    def calculate_historical_features(self, db, team_id):
        return {
            "win_rate": 72.0,
            "trend": 66.0,
            "recent_form": 70.0,
        }


class _FakeSnapshotService:
    def save_snapshot(self, **kwargs):
        return None

    def save_feature_snapshots(self, **kwargs):
        return []


class _FakeCalibrationService:
    def calibrated_confidence(self, raw_confidence, db=None):
        return raw_confidence


class _FakeConfidenceService:
    def calculate_confidence(self, home_score, away_score, home_features, away_features, analytics=None):
        return 65.0


class _FakeModel:
    def __init__(self):
        self.calls = []

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "home_score": 77.0,
            "away_score": 71.5,
            "recommendation": kwargs["home_team_name"],
            "confidence": 70.0,
            "confidence_level": "MODERATE",
            "explanation": {
                "recommendation": kwargs["home_team_name"],
                "score_gap": 5.5,
                "reasons": ["Fake model explanation"],
            },
            "metadata": {
                "model_name": "NBA Prediction Model",
                "version": "NBA-v1",
                "supported_sport": "basketball_nba",
                "build_date": "2026-08-05",
            },
        }


class _FakeRegistry:
    def __init__(self, model):
        self.model = model
        self.calls = []

    def get_model(self, sport, version=None):
        self.calls.append((sport, version))
        return self.model


class _FakeVersionService:
    def __init__(self, versions=None):
        self.versions = versions or {}

    def get_version_for_sport(self, sport, default=None):
        return self.versions.get(sport, default)


def test_prediction_service_routes_through_model_registry(monkeypatch):
    fake_model = _FakeModel()
    fake_registry = _FakeRegistry(fake_model)

    fake_game = SimpleNamespace(
        id=5,
        sport="basketball_nba",
        home_team=SimpleNamespace(
            id=1,
            name="Home Team",
            performance=SimpleNamespace(
                wins=8,
                losses=2,
                offensive_rating=80.0,
                defensive_rating=62.0,
                recent_form=74.0,
            ),
        ),
        away_team=SimpleNamespace(
            id=2,
            name="Away Team",
            performance=SimpleNamespace(
                wins=6,
                losses=4,
                offensive_rating=74.0,
                defensive_rating=66.0,
                recent_form=69.0,
            ),
        ),
        analytics=None,
    )

    monkeypatch.setattr(
        "app.services.prediction_service.game_repository.get_game_with_teams",
        lambda db, game_id: fake_game,
    )

    service = PredictionService(
        model_registry=fake_registry,
        version_service=_FakeVersionService(),
        validation_service=_FakeValidationService(),
        feature_service=_FakeFeatureService(),
        snapshot_service=_FakeSnapshotService(),
        calibration_service=_FakeCalibrationService(),
        confidence_service=_FakeConfidenceService(),
    )

    db = _FakeDB()
    prediction = service.generate_prediction(db, game_id=5)

    assert fake_registry.calls == [("basketball_nba", None)]
    assert len(fake_model.calls) == 1
    assert prediction.game_id == 5
    assert prediction.home_score == 77.0
    assert prediction.away_score == 71.5
    assert prediction.recommendation == "Home Team"
    assert prediction.model_version == "NBA-v1"
    assert prediction.explanation["score_gap"] == 5.5


def test_prediction_service_requests_sport_specific_version_when_available(monkeypatch):
    fake_model = _FakeModel()
    fake_registry = _FakeRegistry(fake_model)

    fake_game = SimpleNamespace(
        id=7,
        sport="basketball_nba",
        home_team=SimpleNamespace(
            id=1,
            name="Home Team",
            performance=SimpleNamespace(
                wins=8,
                losses=2,
                offensive_rating=80.0,
                defensive_rating=62.0,
                recent_form=74.0,
            ),
        ),
        away_team=SimpleNamespace(
            id=2,
            name="Away Team",
            performance=SimpleNamespace(
                wins=6,
                losses=4,
                offensive_rating=74.0,
                defensive_rating=66.0,
                recent_form=69.0,
            ),
        ),
        analytics=None,
    )

    monkeypatch.setattr(
        "app.services.prediction_service.game_repository.get_game_with_teams",
        lambda db, game_id: fake_game,
    )

    service = PredictionService(
        model_registry=fake_registry,
        version_service=_FakeVersionService({"basketball_nba": "NBA-v2"}),
        validation_service=_FakeValidationService(),
        feature_service=_FakeFeatureService(),
        snapshot_service=_FakeSnapshotService(),
        calibration_service=_FakeCalibrationService(),
        confidence_service=_FakeConfidenceService(),
    )

    db = _FakeDB()
    service.generate_prediction(db, game_id=7)

    assert fake_registry.calls == [("basketball_nba", "NBA-v2")]
