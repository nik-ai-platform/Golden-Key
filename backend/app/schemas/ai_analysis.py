from datetime import datetime

from pydantic import BaseModel


class AIAnalysisResponse(BaseModel):

    id: int

    prediction_id: int

    summary: str

    explanation: str

    created_at: datetime

    class Config:
        from_attributes = True
