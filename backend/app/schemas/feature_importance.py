from pydantic import BaseModel


class FeatureContribution(BaseModel):
    feature: str
    value: float
    weight: float
    contribution: float


class PredictionExplanation(BaseModel):
    prediction_id: int
    winner: str
    confidence: float
    top_positive: list[FeatureContribution]
    top_negative: list[FeatureContribution]