from sqlalchemy.orm import Session

from app.services.analytics.confidence_service import (
    ConfidenceService
)


class ConfidenceCalibrationService:
    """Compatibility wrapper for confidence calibration methods."""


    def __init__(
        self,
        confidence_service=None,
    ):
        self.confidence = (
            confidence_service or ConfidenceService()
        )


    def calculate_calibration(
        self,
        db: Session
    ):
        return self.confidence.calibration(db)


    def calibration_error(
        self,
        calibration_data
    ):
        return self.confidence.calibration_error(calibration_data)
