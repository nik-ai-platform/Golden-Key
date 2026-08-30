from datetime import datetime

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):

    id: int | None

    plan: str

    active: bool

    created_at: datetime | None

    class Config:

        from_attributes = True