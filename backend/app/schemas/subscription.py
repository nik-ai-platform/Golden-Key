from datetime import datetime

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):

    id: int

    plan: str

    active: bool

    created_at: datetime

    class Config:

        from_attributes = True