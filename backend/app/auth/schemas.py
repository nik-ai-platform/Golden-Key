from pydantic import BaseModel, EmailStr

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
    new_password: str


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
