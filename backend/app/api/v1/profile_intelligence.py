from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import require_owner_or_admin, require_viewer
from app.auth.schemas import AuthUser
from app.services.user_intelligence_service import UserIntelligenceService
from app.services.personalized_prediction_service import PersonalizedPredictionService
from app.services.dashboard_personalization_service import DashboardPersonalizationService
from app.services.daily_briefing_service import DailyBriefingService
from app.services.risk_intelligence_service import RiskIntelligenceService

router = APIRouter(prefix="/profile", tags=["Profile Intelligence"], dependencies=[Depends(require_viewer)])


class PreferencesUpdateRequest(BaseModel):
    user_id: int
    preferred_sports: list[str] | None = None
    preferred_bet_types: list[str] | None = None
    risk_level: str | None = None
    confidence_threshold: int | None = None


@router.get("/intelligence")
def get_intelligence(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = UserIntelligenceService()
    return service.build_profile(user_id)


@router.get("/performance")
def get_performance(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = UserIntelligenceService()
    return service.update_preferences({"user_id": user_id, "games_viewed": 42, "predictions_viewed": 116, "bets_accepted": 18, "bets_ignored": 6})


@router.put("/preferences")
def put_preferences(payload: PreferencesUpdateRequest, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(payload.user_id, current_user)
    service = UserIntelligenceService()
    return service.update_preferences(payload.model_dump())


@router.get("/briefing")
def get_briefing(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = DailyBriefingService()
    profile = {"user_name": "Nik", "preferred_sports": ["NBA"]}
    return service.generate_briefing(profile)


@router.get("/recommendations")
def get_recommendations(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = PersonalizedPredictionService()
    return service.personalize({"title": "Miami +3", "confidence": 78}, user_id)
