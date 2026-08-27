import app.services.prediction_snapshot_service as prediction_snapshot_service
from app.services.prediction_snapshot_service import (
    PredictionSnapshotService
)


class _FakeDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_save_snapshot_persists_and_returns_snapshot(monkeypatch):
    class _FakeSnapshot:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        prediction_snapshot_service,
        "PredictionSnapshot",
        _FakeSnapshot,
    )

    service = PredictionSnapshotService()
    db = _FakeDB()

    result = service.save_snapshot(
        db=db,
        game_id=101,
        model_version="NPI-v1",
        prediction="Home Team",
        confidence=78.5,
        home_score=84.2,
        away_score=79.4,
        home_features={"strength": 72, "recent_form": 68},
        away_features={"strength": 66, "recent_form": 61},
    )

    assert result is db.added[0]
    assert db.committed is True
    assert db.refreshed == [result]


def test_save_snapshot_sets_expected_fields(monkeypatch):
    class _FakeSnapshot:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        prediction_snapshot_service,
        "PredictionSnapshot",
        _FakeSnapshot,
    )

    service = PredictionSnapshotService()
    db = _FakeDB()

    snapshot = service.save_snapshot(
        db=db,
        game_id=7,
        model_version="NPI-v2",
        prediction="Away Team",
        confidence=64.25,
        home_score=75.0,
        away_score=80.5,
        home_features={"offense": 70},
        away_features={"offense": 74},
    )

    assert snapshot.game_id == 7
    assert snapshot.model_version == "NPI-v2"
    assert snapshot.prediction == "Away Team"
    assert snapshot.confidence == 64.25
    assert snapshot.home_score == 75.0
    assert snapshot.away_score == 80.5
    assert snapshot.home_features == {"offense": 70}
    assert snapshot.away_features == {"offense": 74}


def test_save_snapshot_accepts_empty_feature_maps(monkeypatch):
    class _FakeSnapshot:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        prediction_snapshot_service,
        "PredictionSnapshot",
        _FakeSnapshot,
    )

    service = PredictionSnapshotService()
    db = _FakeDB()

    snapshot = service.save_snapshot(
        db=db,
        game_id=11,
        model_version="NPI-v3",
        prediction="Home",
        confidence=55.0,
        home_score=70.0,
        away_score=69.0,
        home_features={},
        away_features={},
    )

    assert snapshot.home_features == {}
    assert snapshot.away_features == {}
    assert db.committed is True
