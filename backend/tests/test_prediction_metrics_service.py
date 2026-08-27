from app.services.prediction_metrics_service import (
    PredictionMetricsService
)


def test_overall_accuracy_delegates_to_analytics_service():

    class _FakeAnalyticsService:
        def __init__(self):
            self.calls = []

        def calculate_accuracy(self, db=None, evaluations=None):
            self.calls.append((db, evaluations))
            return 66.67

    fake_analytics = _FakeAnalyticsService()
    service = PredictionMetricsService(analytics_service=fake_analytics)
    db = object()

    accuracy = service.overall_accuracy(db)

    assert fake_analytics.calls == [(db, None)]
    assert accuracy == 66.67


def test_accuracy_by_model_version_delegates_to_analytics_service():

    expected = {
        "NPI-v1": {
            "total": 3,
            "correct": 2,
            "accuracy": 66.67,
        }
    }

    class _FakeAnalyticsService:
        def __init__(self):
            self.calls = []

        def model_accuracy(self, db):
            self.calls.append(db)
            return expected

    fake_analytics = _FakeAnalyticsService()
    service = PredictionMetricsService(analytics_service=fake_analytics)
    db = object()

    output = service.accuracy_by_model_version(db)

    assert fake_analytics.calls == [db]
    assert output == expected


def test_accuracy_by_confidence_delegates_to_confidence_service():

    expected = {
        "LOW": 0,
        "MODERATE": 50.0,
        "STRONG": 100.0,
        "ELITE": 100.0,
    }

    class _FakeConfidenceService:
        def __init__(self):
            self.calls = []

        def confidence_buckets(self, db):
            self.calls.append(db)
            return expected

    fake_confidence = _FakeConfidenceService()
    service = PredictionMetricsService(confidence_service=fake_confidence)
    db = object()

    output = service.accuracy_by_confidence(db)

    assert fake_confidence.calls == [db]
    assert output == expected
