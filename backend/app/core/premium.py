from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.core.roles import UserRole
from app.database.session import get_db
from app.services.entitlement_reconciliation_service import PREMIUM_ENTITLEMENT_KEY
from app.services.entitlement_service import has_active_entitlement


def require_premium(user: AuthUser, db: Session) -> AuthUser:
    if user.role == UserRole.ADMIN:
        return user
    if not has_active_entitlement(db, user.id, PREMIUM_ENTITLEMENT_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active Premium access required",
        )
    return user


def require_premium_user(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthUser:
    return require_premium(current_user, db)
