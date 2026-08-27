from pydantic import BaseModel


class ConfidenceBucket(BaseModel):

    label: str

    predictions: int

    accuracy: float


class ConfidenceAnalytics(BaseModel):

    average_confidence: float

    highest_confidence: float

    lowest_confidence: float

    buckets: list[ConfidenceBucket]


class ConfidenceCalibrationBucket(BaseModel):

    label: str

    predictions: int

    predicted_confidence: float

    observed_accuracy: float

    calibration_gap: float

    well_calibrated: bool
