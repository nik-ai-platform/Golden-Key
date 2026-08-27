from types import SimpleNamespace

from app.services.calibration_service import CalibrationService



def _outcome(prediction_id, confidence, correct):
    return SimpleNamespace(
        prediction_id=prediction_id,
        predicted_confidence=confidence,
        prediction_correct=correct,
    )



def test_empty_dataset_returns_zeroed_metrics():
    service = CalibrationService(min_bucket_samples=2)

    result = service.calculate_calibration(outcomes=[])

    assert result["overall_error"] == 0.0
    assert result["mean_calibration_error"] == 0.0
    assert result["maximum_error"] == 0.0
    assert result["bucket_variance"] == 0.0
    assert result["total_predictions"] == 0
    assert all(bucket["predictions"] == 0 for bucket in result["buckets"])



def test_build_confidence_buckets_classifies_predictions_correctly():
    service = CalibrationService(min_bucket_samples=2)
    outcomes = [
        _outcome(1, 55, True),
        _outcome(2, 65, True),
        _outcome(3, 75, False),
        _outcome(4, 85, True),
        _outcome(5, 95, False),
    ]

    buckets = service.build_confidence_buckets(outcomes)
    by_range = {bucket["range"]: bucket for bucket in buckets}

    assert by_range["50-59"]["predictions"] == 1
    assert by_range["60-69"]["predictions"] == 1
    assert by_range["70-79"]["predictions"] == 1
    assert by_range["80-89"]["predictions"] == 1
    assert by_range["90-100"]["predictions"] == 1

    assert by_range["90-100"]["wins"] == 0
    assert by_range["90-100"]["losses"] == 1
    assert by_range["90-100"]["average_confidence"] == 95.0
    assert by_range["90-100"]["accuracy"] == 0.0



def test_calibration_error_calculation_is_correct_and_signed():
    service = CalibrationService(min_bucket_samples=2)

    assert service.calibration_error(91.0, 87.0) == 4.0
    assert service.calibration_error(82.0, 85.0) == -3.0



def test_confidence_adjustment_skips_when_sample_below_threshold():
    service = CalibrationService(min_bucket_samples=3)

    buckets = [
        {
            "range": "90-100",
            "predictions": 2,
            "average_confidence": 94.0,
            "accuracy": 89.0,
        }
    ]

    adjusted = service.calibrated_confidence(95.0, buckets=buckets)

    assert adjusted == 95.0



def test_confidence_adjustment_applies_when_sample_meets_threshold():
    service = CalibrationService(min_bucket_samples=3)

    buckets = [
        {
            "range": "90-100",
            "predictions": 30,
            "average_confidence": 94.0,
            "accuracy": 89.0,
        }
    ]

    adjusted = service.calibrated_confidence(95.0, buckets=buckets)

    # bucket error is +5.0, so raw 95.0 adjusts to 90.0
    assert adjusted == 90.0



def test_duplicate_outcomes_do_not_distort_statistics():
    service = CalibrationService(min_bucket_samples=2)

    outcomes = [
        _outcome(101, 95, True),
        _outcome(101, 95, False),
        _outcome(102, 92, False),
    ]

    result = service.calculate_calibration(outcomes=outcomes)
    bucket = next(item for item in result["buckets"] if item["range"] == "90-100")

    # prediction_id 101 should count once after dedupe
    assert result["total_predictions"] == 2
    assert bucket["predictions"] == 2
    assert bucket["wins"] == 1
    assert bucket["losses"] == 1
