from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_owner_or_admin, require_viewer
from app.auth.schemas import AuthUser
from app.database.session import get_db
from app.services.personalization_service import PersonalizationService

router = APIRouter(prefix="/profile", tags=["Personalization"], dependencies=[Depends(require_viewer)])


class ProfileUpdateRequest(BaseModel):
    user_id: int
    risk_level: str | None = None
    preferred_sports: list[str] | None = None
    preferred_markets: list[str] | None = None
    betting_style: str | None = None


class PreferencesUpdateRequest(BaseModel):
    user_id: int
    minimum_confidence: int | None = None
    minimum_edge: float | None = None
    max_parlay_legs: int | None = None


class FeedbackRequest(BaseModel):
    user_id: int
    prediction_helpful: bool | None = None
    recommendation_used: bool | None = None
    confidence_accuracy: float | None = None
    user_rating: int | None = None
    comments: str | None = None


@router.get("")
def get_profile(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = PersonalizationService()
    return service.get_user_profile(user_id)


@router.put("")
def put_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(payload.user_id, current_user)
    service = PersonalizationService()
    return service.save_user_profile(db, payload.model_dump())


@router.get("/preferences")
def get_preferences(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    return {"minimum_confidence": 75, "minimum_edge": 3, "max_parlay_legs": 3}


@router.put("/preferences")
def put_preferences(payload: PreferencesUpdateRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(payload.user_id, current_user)
    service = PersonalizationService()
    return service.save_preferences(db, payload.model_dump())


@router.get("/recommendations/personalized")
def get_personalized_recommendations(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = PersonalizationService()
    predictions = [{"id": 1, "confidence": 90, "edge": 4.5, "winner": "DAL", "parlay": False}]
    profile = {"risk_level": "CONSERVATIVE"}
    return service.personalize_predictions(predictions, profile)


@router.post("/feedback")
def post_feedback(payload: FeedbackRequest, db: Session = Depends(get_db), current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(payload.user_id, current_user)
    service = PersonalizationService()
    return service.save_feedback(db, payload.model_dump())
