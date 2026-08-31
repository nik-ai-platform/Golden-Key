from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.hashing import HashingService
from app.auth.schemas import AuthUser
from app.auth.service import AuthenticationService
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository


class PersistentUserNotFoundError(Exception):
    pass


def resolve_existing_persistent_user(
    db: Session,
    current_user: AuthUser,
) -> User:
    if current_user.id != 0:
        user = db.get(User, current_user.id)
    else:
        user = UserRepository().get_by_email(db, current_user.email.lower())

    if user is None:
        raise PersistentUserNotFoundError("Authenticated user has no persistent account")

    return user


def hydrate_recovery_state(
    db: Session,
    current_user: AuthUser,
) -> AuthUser:
    try:
        user = resolve_existing_persistent_user(db, current_user)
    except PersistentUserNotFoundError:
        recovery_email_masked = None
        recovery_email_verified = False
    else:
        recovery_email_masked = (
            AuthenticationService.mask_email(user.recovery_email)
            if user.recovery_email
            else None
        )
        recovery_email_verified = bool(user.recovery_email_verified)

    return current_user.model_copy(
        update={
            "recovery_email_masked": recovery_email_masked,
            "recovery_email_verified": recovery_email_verified,
        }
    )


def resolve_persistent_user_id(
    db: Session,
    current_user: AuthUser,
) -> int:
    """
    Return a real users.id for an authenticated account.

    Normal registered users already exist in the users table.
    The configured master/demo account authenticates with synthetic
    id=0, so create its backing users row the first time persistence
    is required.
    """
    repository = UserRepository()

    existing = repository.get_by_email(
        db,
        current_user.email.lower(),
    )

    if existing is not None:
        return int(existing.id)

    if current_user.id != 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists.",
        )

    if (
        current_user.email.lower()
        != settings.AUTH_DEMO_EMAIL.lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user could not be resolved.",
        )

    base_username = current_user.username.strip() or "goldenkey-admin"
    username = base_username
    suffix = 1

    while repository.get_by_username(db, username) is not None:
        suffix += 1
        username = f"{base_username}-{suffix}"

    persistent_user = repository.create(
        db,
        username=username,
        email=current_user.email.lower(),
        hashed_password=HashingService().hash_password(
            settings.AUTH_DEMO_PASSWORD
        ),
        role=current_user.role,
        is_active=True,
    )

    return int(persistent_user.id)