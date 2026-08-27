from datetime import UTC, datetime

from app.services.training_dataset_service import TrainingDatasetService


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class _FakeDB:
    def __init__(self, outcomes, predictions, games, features):
        self.outcomes = outcomes
        self.predictions = predictions
        self.games = games
        self.features = features

    def query(self, model):
        name = getattr(model, "__name__", "")

        if name == "PredictionOutcome":
            return _FakeQuery(self.outcomes)

        if name == "NikScore":
            return _FakeQuery(self.predictions)

        if name == "Game":
            return _FakeQuery(self.games)

        if name == "FeatureSnapshot":
            return _FakeQuery(self.features)

        return _FakeQuery([])


def _row(**kwargs):
    class _Object:
        pass

    obj = _Object()
    for key, value in kwargs.items():
        setattr(obj, key, value)
    return obj


def test_dataset_generation_is_repeatable():
    service = TrainingDatasetService()
    now = datetime.now(UTC)

    db = _FakeDB(
        outcomes=[
            _row(id=1, prediction_id=10, game_id=20, actual_winner="home", prediction_correct=True, created_at=now),
        ],
        predictions=[
            _row(id=10, confidence=84.0, model_version="NPI-v3"),
        ],
        games=[
            _row(id=20, sport="WNBA", home_team=None, away_team=None),
        ],
        features=[
            _row(id=1, prediction_id=10, feature_name="home_strength", feature_value=82.4),
            _row(id=2, prediction_id=10, feature_name="away_strength", feature_value=76.8),
        ],
    )

    first = service.build_dataset(now, now, db=db)
    second = service.build_dataset(now, now, db=db)

    assert first == second


def test_historical_features_are_read_from_snapshots_not_recalculated():
    service = TrainingDatasetService()
    now = datetime.now(UTC)

    db = _FakeDB(
        outcomes=[
            _row(id=1, prediction_id=15, game_id=25, actual_winner="away", prediction_correct=False, created_at=now),
        ],
        predictions=[
            _row(id=15, confidence=64.5, model_version="NPI-v4"),
        ],
        games=[
            _row(id=25, sport="WNBA", home_team=None, away_team=None),
        ],
        features=[
            _row(id=1, prediction_id=15, feature_name="home_momentum", feature_value=91.0),
            _row(id=2, prediction_id=15, feature_name="away_momentum", feature_value=72.0),
        ],
    )

    dataset = service.build_dataset(now, now, db=db)

    assert dataset[0]["home_momentum"] == 91.0
    assert dataset[0]["away_momentum"] == 72.0


def test_invalid_records_are_rejected():
    service = TrainingDatasetService()

    dataset = [
        {
            "sport": "WNBA",
            "confidence": "high",
            "winner": "neutral",
            "correct": "yes",
            "model_version": "NPI-v4",
        }
    ]

    result = service.validate_dataset(dataset)

    assert result["valid"] is False
    assert len(result["errors"]) >= 2


def test_export_dataset_csv_uses_stable_columns():
    service = TrainingDatasetService()
    service._latest_dataset = [
        {
            "sport": "WNBA",
            "confidence": 84.0,
            "winner": "home",
            "correct": True,
            "model_version": "NPI-v3",
            "home_strength": 82.4,
            "away_strength": 76.8,
        }
    ]

    output = service.export_dataset("csv")

    assert "sport,confidence,winner,correct,model_version,away_strength,home_strength" in output
    assert "WNBA,84.0,home,True,NPI-v3,76.8,82.4" in output