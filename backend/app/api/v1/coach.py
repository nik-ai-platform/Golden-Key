from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import require_owner_or_admin, require_viewer
from app.auth.schemas import AuthUser
from app.services.ai_coach_service import AICoachService

router = APIRouter(prefix="/coach", tags=["Coach"], dependencies=[Depends(require_viewer)])


class CoachChatRequest(BaseModel):
    user_id: int
    question: str | None = None
    message: str | None = None


@router.post("/chat")
def chat(payload: CoachChatRequest, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(payload.user_id, current_user)
    user_id = payload.user_id
    question = payload.question or payload.message or ""
    service = AICoachService()
    return service.answer_question(user_id, question)


@router.get("/history")
def history(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = AICoachService()
    return {
        "user_id": user_id,
        "history": [
            {
                "message": item.message,
                "response": item.response,
                "context": item.context,
            }
            for item in service.conversations
            if item.user_id == user_id
        ],
    }


@router.get("/briefing")
def briefing(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = AICoachService()
    return service.provide_guidance({"profile": {"risk_level": "MODERATE", "preferred_sports": ["NBA"], "bankroll": 5000}, "user_id": user_id})


@router.get("/recommendations")
def recommendations(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = AICoachService()
    return {
        "user_id": user_id,
        "recommendations": [
            service.explain_bet(1),
            service.review_strategy(1),
        ],
    }
