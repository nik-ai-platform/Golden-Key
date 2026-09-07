from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProviderSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    provider: str
    external_customer_id: str | None
    external_subscription_id: str | None
    external_product_id: str | None
    plan: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_end: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)