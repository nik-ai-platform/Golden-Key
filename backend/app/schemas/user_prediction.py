from datetime import datetime

from pydantic import BaseModel


class SavePredictionRequest(BaseModel):

    prediction_id: int


class UserPredictionResponse(BaseModel):

    id: int

    prediction_id: int

    created_at: datetime

    class Config:

        from_attributes = True