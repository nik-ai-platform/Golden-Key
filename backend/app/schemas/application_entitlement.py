from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationEntitlementResponse(BaseModel):
    id: int
    user_id: int
    entitlement_key: str
    plan: str
    status: str
    source_provider: str | None
    source_subscription_id: int | None
    starts_at: datetime
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerEntitlementResponse(BaseModel):
    entitlement_key: str
    plan: str
    status: str
    starts_at: datetime
    ends_at: datetime | None
    active: bool