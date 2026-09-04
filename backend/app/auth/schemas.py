from pydantic import BaseModel, EmailStr, Field

from app.core.roles import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=256)


class RecoveryEmailRequest(BaseModel):
    recovery_email: EmailStr


class RecoveryCodeRequest(BaseModel):
    code: str = Field(max_length=128)


class ForgotEmailRequest(BaseModel):
    recovery_email: str = Field(max_length=320)


class ForgotEmailVerifyRequest(ForgotEmailRequest, RecoveryCodeRequest):
    pass


class MaskedEmailResponse(BaseModel):
    email: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class VerifyEmailTokenRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str


class AuthUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    email_verified: bool = False
    recovery_email_masked: str | None = None
    recovery_email_verified: bool = False
