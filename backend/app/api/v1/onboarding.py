from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_owner_or_admin, require_viewer
from app.auth.hashing import HashingService
from app.auth.schemas import AuthUser
from app.auth.service import AuthenticationService
from app.core.roles import UserRole
from app.database.session import get_db
from app.models.bankroll import Bankroll
from app.models.subscription import Subscription
from app.models.user_profile import UserProfile
from app.repositories.user_repository import UserRepository


router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)
    accept_terms: bool = True


class FavoriteSportsRequest(BaseModel):
    user_id: int
    preferred_sports: list[str] = Field(default_factory=list)


class RiskProfileRequest(BaseModel):
    user_id: int
    risk_level: str = Field(..., min_length=3, max_length=32)


class BankrollSettingsRequest(BaseModel):
    user_id: int
    total_amount: float = Field(..., gt=0)
    unit_percentage: float = Field(..., gt=0)
    max_daily_risk: float = Field(..., gt=0)


class CompleteOnboardingRequest(BaseModel):
    user_id: int


def _get_or_create_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile:
        return profile

    profile = UserProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _get_or_create_bankroll(db: Session, user_id: int) -> Bankroll:
    bankroll = db.query(Bankroll).filter(Bankroll.user_id == user_id).first()
    if bankroll:
        return bankroll

    bankroll = Bankroll(user_id=user_id)
    db.add(bankroll)
    db.commit()
    db.refresh(bankroll)
    return bankroll


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if not payload.accept_terms:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Terms acceptance is required")

    user_repository = UserRepository()

    if user_repository.get_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    if user_repository.get_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    hashed_password = HashingService().hash_password(payload.password)
    user = user_repository.create(
        db,
        username=payload.username,
        email=str(payload.email),
        hashed_password=hashed_password,
        role=UserRole.VIEWER,
        is_active=True,
    )

    AuthenticationService().request_email_verification(db, str(payload.email))

    return {
        "user_id": user.id,
        "email": user.email,
        "next_step": "verify_email",
        "message": "Account created. Verification email has been queued.",
    }


@router.get("/status")
def onboarding_status(
    user_id: int,
    current_user: AuthUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    require_owner_or_admin(user_id, current_user)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    bankroll = db.query(Bankroll).filter(Bankroll.user_id == user_id).first()

    sports_completed = bool(profile and profile.preferred_sports)
    risk_completed = bool(profile and profile.risk_level)
    bankroll_completed = bool(bankroll and bankroll.total_amount and bankroll.unit_percentage and bankroll.max_daily_risk)

    completed_steps = sum([1 if sports_completed else 0, 1 if risk_completed else 0, 1 if bankroll_completed else 0])

    return {
        "user_id": user_id,
        "steps": {
            "register": True,
            "verify_email": current_user.email_verified,
            "favorite_sports": sports_completed,
            "risk_profile": risk_completed,
            "bankroll_settings": bankroll_completed,
        },
        "progress_percent": round((completed_steps / 3) * 100),
        "next_route": "/dashboard" if completed_steps == 3 else "/onboarding",
    }


@router.put("/favorite-sports")
def set_favorite_sports(
    payload: FavoriteSportsRequest,
    current_user: AuthUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    require_owner_or_admin(payload.user_id, current_user)

    profile = _get_or_create_profile(db, payload.user_id)
    profile.preferred_sports = payload.preferred_sports
    db.add(profile)
    db.commit()

    return {
        "status": "updated",
        "user_id": payload.user_id,
        "preferred_sports": payload.preferred_sports,
    }


@router.put("/risk-profile")
def set_risk_profile(
    payload: RiskProfileRequest,
    current_user: AuthUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    require_owner_or_admin(payload.user_id, current_user)

    profile = _get_or_create_profile(db, payload.user_id)
    profile.risk_level = payload.risk_level.upper()
    db.add(profile)
    db.commit()

    return {
        "status": "updated",
        "user_id": payload.user_id,
        "risk_level": profile.risk_level,
    }


@router.put("/bankroll")
def set_bankroll_settings(
    payload: BankrollSettingsRequest,
    current_user: AuthUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    require_owner_or_admin(payload.user_id, current_user)

    bankroll = _get_or_create_bankroll(db, payload.user_id)
    bankroll.total_amount = payload.total_amount
    bankroll.unit_percentage = payload.unit_percentage
    bankroll.max_daily_risk = payload.max_daily_risk
    db.add(bankroll)
    db.commit()

    return {
        "status": "updated",
        "user_id": payload.user_id,
        "bankroll": {
            "total_amount": bankroll.total_amount,
            "unit_percentage": bankroll.unit_percentage,
            "max_daily_risk": bankroll.max_daily_risk,
        },
    }


@router.post("/complete")
def complete_onboarding(
    payload: CompleteOnboardingRequest,
    current_user: AuthUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    require_owner_or_admin(payload.user_id, current_user)

    profile = _get_or_create_profile(db, payload.user_id)
    profile.betting_style = profile.betting_style or "balanced"
    db.add(profile)
    db.commit()

    return {
        "status": "completed",
        "user_id": payload.user_id,
        "dashboard_route": "/dashboard",
    }


@router.get("/bootstrap")
def onboarding_bootstrap(
    user_id: int,
    current_user: AuthUser = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    require_owner_or_admin(user_id, current_user)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    bankroll = db.query(Bankroll).filter(Bankroll.user_id == user_id).first()
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()

    return {
        "profile": {
            "user_id": user_id,
            "risk_level": getattr(profile, "risk_level", None),
            "preferred_sports": getattr(profile, "preferred_sports", []) or [],
        },
        "preferences": {
            "favorite_teams": [],
            "notifications": {
                "email": True,
                "push": True,
                "prediction_alerts": True,
                "pipeline_alerts": True,
            },
        },
        "subscription": {
            "plan": getattr(subscription, "plan", "FREE"),
            "status": getattr(subscription, "status", "inactive"),
        },
        "bankroll": {
            "total_amount": getattr(bankroll, "total_amount", None),
            "unit_percentage": getattr(bankroll, "unit_percentage", None),
            "max_daily_risk": getattr(bankroll, "max_daily_risk", None),
        },
        "history": {
            "prediction_views": 0,
            "portfolio_actions": 0,
        },
    }