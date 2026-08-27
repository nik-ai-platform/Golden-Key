from datetime import datetime
from types import SimpleNamespace

from app.services.analytics import confidence_service as confidence_module
from app.services.analytics.confidence_service import ConfidenceService


def test_get_bucket_statistics_groups_and_scores(monkeypatch):
    evaluations = [
        SimpleNamespace(confidence=50, correct=True),
        SimpleNamespace(confidence=60, correct=False),
        SimpleNamespace(confidence=80, correct=True),
        SimpleNamespace(confidence=95, correct=False),
    ]

    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: evaluations,
    )

    service = ConfidenceService()
    db = object()

    buckets = service.get_bucket_statistics(db)

    assert [bucket.label for bucket in buckets] == ["LOW", "MODERATE", "STRONG", "ELITE"]
    assert [bucket.predictions for bucket in buckets] == [1, 1, 1, 1]
    assert [bucket.accuracy for bucket in buckets] == [100.0, 0.0, 100.0, 0.0]


def test_get_average_confidence_and_distribution(monkeypatch):
    evaluations = [
        SimpleNamespace(confidence=55, correct=True),
        SimpleNamespace(confidence=75, correct=False),
        SimpleNamespace(confidence=90, correct=True),
    ]

    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: evaluations,
    )

    service = ConfidenceService()
    db = object()

    assert service.get_average_confidence(db) == 73.33

    distribution = service.get_confidence_distribution(db)

    assert distribution.average_confidence == 73.33
    assert distribution.highest_confidence == 90
    assert distribution.lowest_confidence == 55
    assert len(distribution.buckets) == 4


def test_get_confidence_history_builds_rolling_trend(monkeypatch):
    evaluations = [
        SimpleNamespace(confidence=80, correct=True, created_at=datetime(2025, 1, 3)),
        SimpleNamespace(confidence=60, correct=False, created_at=datetime(2025, 1, 1)),
        SimpleNamespace(confidence=70, correct=True, created_at=datetime(2025, 1, 2)),
    ]

    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: evaluations,
    )

    service = ConfidenceService()
    db = object()

    history = service.get_confidence_history(db)

    assert [point["confidence"] for point in history] == [60, 70, 80]
    assert [point["rolling_average"] for point in history] == [60.0, 65.0, 70.0]


def test_empty_evaluations_return_safe_defaults(monkeypatch):
    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: [],
    )

    service = ConfidenceService()
    db = object()

    assert service.get_average_confidence(db) == 0
    assert service.get_confidence_history(db) == []

    distribution = service.get_confidence_distribution(db)
    assert distribution.average_confidence == 0
    assert distribution.highest_confidence == 0
    assert distribution.lowest_confidence == 0
    assert [bucket.predictions for bucket in distribution.buckets] == [0, 0, 0, 0]


def test_get_confidence_calibration_compares_predicted_to_observed(monkeypatch):
    evaluations = [
        SimpleNamespace(confidence=92, correct=True),
        SimpleNamespace(confidence=94, correct=True),
        SimpleNamespace(confidence=96, correct=True),
        SimpleNamespace(confidence=94, correct=True),
        SimpleNamespace(confidence=94, correct=False),
        SimpleNamespace(confidence=94, correct=True),
        SimpleNamespace(confidence=94, correct=True),
        SimpleNamespace(confidence=94, correct=True),
        SimpleNamespace(confidence=94, correct=True),
        SimpleNamespace(confidence=94, correct=True),
    ]

    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: evaluations,
    )

    service = ConfidenceService()
    db = object()

    calibration = service.get_confidence_calibration(db)
    elite = next(bucket for bucket in calibration if bucket.label == "ELITE")

    assert elite.predictions == 10
    assert elite.predicted_confidence == 94.0
    assert elite.observed_accuracy == 90.0
    assert elite.calibration_gap == 4.0
    assert elite.well_calibrated is True
