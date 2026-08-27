from pydantic import BaseModel


class ModelPromotionRequest(BaseModel):

    model_version: str
    sport: str
    approved_by: str | None = None
    notes: str | None = None


class ModelEvaluationResponse(BaseModel):

    eligible: bool
    reason: str
    games: int
    ats_win_rate: float
