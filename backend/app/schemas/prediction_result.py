from datetime import datetime

from pydantic import BaseModel


class PredictionResultCreate(BaseModel):

    prediction_id: int

    actual_result: str

    predicted_result: str

    outcome: str

    profit_loss: float = 0


class PredictionResultResponse(
    PredictionResultCreate
):

    id: int

    created_at: datetime

    class Config:

        from_attributes = True