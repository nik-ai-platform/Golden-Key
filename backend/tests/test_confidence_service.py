from types import SimpleNamespace

from app.services.analytics import confidence_service as confidence_module
from app.services.analytics.confidence_service import ConfidenceService


def test_bucket_boundaries_are_correct(monkeypatch):
    evaluations = [
        SimpleNamespace(confidence=55, correct=True),
        SimpleNamespace(confidence=56, correct=False),
        SimpleNamespace(confidence=75, correct=True),
        SimpleNamespace(confidence=76, correct=False),
        SimpleNamespace(confidence=90, correct=True),
        SimpleNamespace(confidence=91, correct=False),
    ]

    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: evaluations,
    )

    service = ConfidenceService()
    buckets = service.get_bucket_statistics(object())

    by_label = {bucket.label: bucket for bucket in buckets}

    assert by_label["LOW"].predictions == 1
    assert by_label["MODERATE"].predictions == 2
    assert by_label["STRONG"].predictions == 2
    assert by_label["ELITE"].predictions == 1


def test_empty_dataset_returns_zeroed_values(monkeypatch):
    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: [],
    )

    service = ConfidenceService()
    db = object()

    distribution = service.get_confidence_distribution(db)

    assert distribution.average_confidence == 0
    assert distribution.highest_confidence == 0
    assert distribution.lowest_confidence == 0
    assert [bucket.predictions for bucket in distribution.buckets] == [0, 0, 0, 0]


def test_average_confidence_is_calculated_correctly(monkeypatch):
    evaluations = [
        SimpleNamespace(confidence=60, correct=True),
        SimpleNamespace(confidence=80, correct=True),
        SimpleNamespace(confidence=90, correct=False),
    ]

    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: evaluations,
    )

    service = ConfidenceService()

    assert service.get_average_confidence(object()) == 76.67


def test_calibration_handles_missing_evaluations_gracefully(monkeypatch):
    monkeypatch.setattr(
        confidence_module.analytics_repository,
        "get_evaluations",
        lambda db: [],
    )

    service = ConfidenceService()

    calibration = service.calibration(object())

    assert calibration["0-50"] == {"predictions": 0, "accuracy": 0}
    assert calibration["91-100"] == {"predictions": 0, "accuracy": 0}
    assert service.calibration_error(calibration) == 0
