from types import SimpleNamespace

import app.services.prediction_evaluation_service as prediction_evaluation_service
from app.services.prediction_evaluation_service import (
    PredictionEvaluationService
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


def test_evaluate_marks_correct_when_prediction_matches(monkeypatch):
    class _FakePredictionEvaluation:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        prediction_evaluation_service,
        "PredictionEvaluation",
        _FakePredictionEvaluation,
    )

    service = PredictionEvaluationService()
    db = _FakeDB()

    snapshot = SimpleNamespace(
        id=10,
        prediction="7",
        confidence=81.5,
    )

    result = service.evaluate(
        db=db,
        snapshot=snapshot,
        actual_winner_id=7,
    )

    assert result.correct is True
    assert result.snapshot_id == 10
    assert result.predicted_team == "7"
    assert result.actual_winner == 7
    assert result.confidence == 81.5
    assert db.added == [result]
    assert db.committed is True
    assert db.refreshed == [result]


def test_evaluate_marks_incorrect_when_prediction_differs(monkeypatch):
    class _FakePredictionEvaluation:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        prediction_evaluation_service,
        "PredictionEvaluation",
        _FakePredictionEvaluation,
    )

    service = PredictionEvaluationService()
    db = _FakeDB()

    snapshot = SimpleNamespace(
        id=22,
        prediction="3",
        confidence=64.0,
    )

    result = service.evaluate(
        db=db,
        snapshot=snapshot,
        actual_winner_id=9,
    )

    assert result.correct is False
    assert result.snapshot_id == 22
    assert result.predicted_team == "3"
    assert result.actual_winner == 9
    assert result.confidence == 64.0


def test_evaluate_treats_numeric_actual_winner_as_string_match(monkeypatch):
    class _FakePredictionEvaluation:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        prediction_evaluation_service,
        "PredictionEvaluation",
        _FakePredictionEvaluation,
    )

    service = PredictionEvaluationService()
    db = _FakeDB()

    snapshot = SimpleNamespace(
        id=30,
        prediction="12",
        confidence=90.0,
    )

    result = service.evaluate(
        db=db,
        snapshot=snapshot,
        actual_winner_id=12,
    )

    assert result.correct is True
    assert result.actual_winner == 12
