from app.services.confidence_calibration_service import (
    ConfidenceCalibrationService
)


def test_calculate_calibration_delegates_to_confidence_service():

    class _FakeConfidenceService:
        def __init__(self):
            self.calls = []

        def calibration(self, db):
            self.calls.append(db)
            return {"0-50": {"predictions": 1, "accuracy": 100.0}}

    fake = _FakeConfidenceService()
    service = ConfidenceCalibrationService(confidence_service=fake)
    db = object()

    result = service.calculate_calibration(db)

    assert fake.calls == [db]
    assert result == {"0-50": {"predictions": 1, "accuracy": 100.0}}


def test_calibration_error_delegates_to_confidence_service():

    class _FakeConfidenceService:
        def __init__(self):
            self.calls = []

        def calibration_error(self, calibration_data):
            self.calls.append(calibration_data)
            return 12.34

    fake = _FakeConfidenceService()
    service = ConfidenceCalibrationService(confidence_service=fake)
    calibration_data = {"51-60": {"predictions": 2, "accuracy": 50.0}}

    result = service.calibration_error(calibration_data)

    assert fake.calls == [calibration_data]
    assert result == 12.34
