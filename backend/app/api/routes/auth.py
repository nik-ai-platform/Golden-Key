from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_auth_service, get_current_user, oauth2_scheme
from app.auth.schemas import (
    AccessTokenResponse,
    AuthUser,
    EmailVerificationRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    VerifyEmailTokenRequest,
)
from app.auth.service import AuthenticationService
from app.database.session import get_db


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    token = auth.login(db, payload.email, payload.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return token


@router.get("/me", response_model=AuthUser)
def me(
    current_user: AuthUser = Depends(get_current_user),
):
    return current_user


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    payload: RefreshTokenRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    try:
        return auth.refresh(db, payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    access_token: str | None = Depends(oauth2_scheme),
    _: AuthUser = Depends(get_current_user),
    auth: AuthenticationService = Depends(get_auth_service),
):
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    auth.revoke_session(access_token, payload.refresh_token)
    return MessageResponse(message="Session revoked")


@router.post("/password-reset", response_model=MessageResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    auth.request_password_reset(db, str(payload.email))
    return MessageResponse(message="If the account exists, a reset email has been queued")


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    if not auth.reset_password(db, payload.token, payload.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    return MessageResponse(message="Password updated")


@router.post("/email-verification", response_model=MessageResponse)
def request_email_verification(
    payload: EmailVerificationRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    auth.request_email_verification(db, str(payload.email))
    return MessageResponse(message="If the account exists, a verification email has been queued")


@router.post("/email-verification/confirm", response_model=MessageResponse)
def confirm_email_verification(
    payload: VerifyEmailTokenRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    if not auth.verify_email(db, payload.token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
    return MessageResponse(message="Email verified")