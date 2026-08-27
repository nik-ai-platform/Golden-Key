from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionCreateRequest(BaseModel):
    plan: str = Field(..., description="Subscription plan")
    user_id: int = Field(default=1, description="User identifier")


class SubscriptionResponse(BaseModel):
    user_id: int
    plan: str
    status: str


class BillingWebhookRequest(BaseModel):
    provider: str = Field(default="stripe")
    event_type: str = Field(default="checkout.completed")


class ApiKeyCreateRequest(BaseModel):
    owner: int = Field(default=1)
    quota: int = Field(default=1000)


class ApiKeyResponse(BaseModel):
    key: str
    owner: int
    quota: int


class OrganizationCreateRequest(BaseModel):
    name: str
    owner_id: int = Field(default=1)


class OrganizationResponse(BaseModel):
    id: Optional[int] = None
    name: str
    owner_id: int
    plan: str = "FREE"


class PermissionCheckResponse(BaseModel):
    feature: str
    allowed: bool
