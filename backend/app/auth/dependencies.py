from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import JWTError
from app.auth.schemas import AuthUser
from app.auth.service import AuthenticationService
from app.core.roles import UserRole
from app.database.session import get_db


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_auth_service() -> AuthenticationService:
    return AuthenticationService()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    auth: AuthenticationService = Depends(get_auth_service),
    db: Session = Depends(get_db),
) -> AuthUser:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        return auth.current_user(db, token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def require_admin(
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    return require_roles(UserRole.ADMIN)(current_user)


def require_analyst(
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    return require_roles(UserRole.ADMIN, UserRole.ANALYST)(current_user)


def require_viewer(
    current_user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    return require_roles(
        UserRole.ADMIN,
        UserRole.ANALYST,
        UserRole.VIEWER,
    )(current_user)


def require_roles(*roles: UserRole):
    def _dependency(current_user: AuthUser) -> AuthUser:
        allowed = {role.value for role in roles}
        if current_user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return _dependency


def require_owner_or_admin(resource_owner_id: int, current_user: AuthUser) -> AuthUser:
    if current_user.role == UserRole.ADMIN:
        return current_user
    if int(resource_owner_id) != int(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: ownership mismatch",
        )
    return current_user
