from types import SimpleNamespace

from app.services.accuracy_analytics_service import (
    AccuracyAnalyticsService
)


def _db_with_results(results):
    class _Query:
        def all(self):
            return results

    class _DB:
        def query(self, _model):
            return _Query()

    return _DB()


def test_get_overall_accuracy_returns_zero_when_no_results():
    service = AccuracyAnalyticsService()
    db = _db_with_results([])

    accuracy = service.get_overall_accuracy(db)

    assert accuracy == 0


def test_get_overall_accuracy_calculates_percentage():
    service = AccuracyAnalyticsService()

    results = [
        SimpleNamespace(correct=True, confidence=80),
        SimpleNamespace(correct=False, confidence=60),
        SimpleNamespace(correct=True, confidence=95),
    ]
    db = _db_with_results(results)

    accuracy = service.get_overall_accuracy(db)

    assert accuracy == 66.67


def test_get_confidence_accuracy_groups_into_buckets():

    service = AccuracyAnalyticsService()

    results = [
        SimpleNamespace(correct=True, confidence=50),
        SimpleNamespace(correct=False, confidence=70),
        SimpleNamespace(correct=True, confidence=85),
        SimpleNamespace(correct=True, confidence=95),
    ]
    db = _db_with_results(results)

    summary = service.get_confidence_accuracy(db)

    assert summary == {
        "LOW": 100.0,
        "MODERATE": 0.0,
        "STRONG": 100.0,
        "ELITE": 100.0,
    }


def test_uses_injected_services_for_accuracy_and_confidence():

    class _FakeAnalyticsService:
        def __init__(self):
            self.calls = []

        def calculate_accuracy(self, db=None, evaluations=None):
            self.calls.append((db, evaluations))
            return 88.88

    class _FakeConfidenceService:
        def __init__(self):
            self.calls = []

        def confidence_buckets(self, db):
            self.calls.append(db)
            return {"LOW": 0, "MODERATE": 100.0, "STRONG": 100.0, "ELITE": 100.0}

    fake_analytics = _FakeAnalyticsService()
    fake_confidence = _FakeConfidenceService()
    service = AccuracyAnalyticsService(
        analytics_service=fake_analytics,
        confidence_service=fake_confidence,
    )
    db = object()

    overall = service.get_overall_accuracy(db)
    buckets = service.get_confidence_accuracy(db)

    assert fake_analytics.calls == [(db, None)]
    assert fake_confidence.calls == [db]
    assert overall == 88.88
    assert buckets["MODERATE"] == 100.0
