from pydantic import BaseModel


class ModelMetric(BaseModel):
    accuracy: float
    calibration: float
    average_confidence: float
    predictions: int


class ModelComparison(BaseModel):
    current_model: ModelMetric
    candidate_model: ModelMetric
    winner: str