from pydantic import BaseModel, ConfigDict, Field


class AppleTransactionVerificationRequest(BaseModel):
    signedTransaction: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class AppleNotificationRequest(BaseModel):
    signedPayload: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class AppleWebhookResponse(BaseModel):
    status: str
    duplicate: bool