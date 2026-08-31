from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import create_user, get_user_by_email, get_user_by_username


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", response_model=UserResponse)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    if get_user_by_email(db, str(payload.email)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    if get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    return create_user(
        db,
        str(payload.email),
        payload.username,
        payload.password,
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


PASSWORD_RESET_MESSAGE = (
    "If an account exists for that email, password reset instructions have been sent."
)


@router.post("/forgot-password", response_model=MessageResponse)
@router.post("/password-reset", response_model=MessageResponse, include_in_schema=False)
def request_password_reset(
    payload: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    delivery = auth.request_password_reset(db, str(payload.email))
    if delivery is not None:
        background_tasks.add_task(auth.deliver_password_reset, delivery)
    return MessageResponse(message=PASSWORD_RESET_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
@router.post("/password-reset/confirm", response_model=MessageResponse, include_in_schema=False)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    if not auth.reset_password(db, payload.token, payload.new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    return MessageResponse(message="Password updated")


@router.post("/forgot-email", response_model=MessageResponse)
def forgot_email():
    return MessageResponse(
        message=(
            "If you no longer remember the email associated with your Golden Key account, "
            "contact support for account recovery."
        )
    )


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