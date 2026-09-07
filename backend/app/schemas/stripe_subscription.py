from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutSessionCreateRequest(BaseModel):
    plan: str = Field(min_length=1, max_length=64)


class StripeSessionResponse(BaseModel):
    url: str


class CustomerProviderSubscriptionResponse(BaseModel):
    provider: str
    plan: str
    status: str
    current_period_end: datetime | None
    trial_end: datetime | None
    cancel_at_period_end: bool

    model_config = ConfigDict(from_attributes=True)


class SubscriptionOverviewResponse(BaseModel):
    entitlement_key: str
    plan: str
    status: str
    active: bool
    starts_at: datetime | None
    ends_at: datetime | None
    provider_subscriptions: list[CustomerProviderSubscriptionResponse]


class StripeWebhookResponse(BaseModel):
    status: str
    duplicate: bool