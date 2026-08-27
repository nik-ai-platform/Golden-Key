from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.services.ai_assistant_service import AIAssistantService

router = APIRouter(prefix="/assistant", tags=["Assistant"], dependencies=[Depends(require_viewer)])


class AssistantMessageRequest(BaseModel):
    message: str


def _assistant_user(current_user: AuthUser):
    return type(
        "User",
        (),
        {
            "id": current_user.id,
            "profile": {
                "risk_level": "Moderate",
                "bankroll": 5000,
                "favorite_team": "Atlanta Hawks",
                "favorite_sports": ["NBA", "NCAAB"],
                "betting_style": "underdog value",
            },
        },
    )()


@router.post("/message")
def send_message(payload: AssistantMessageRequest, current_user: AuthUser = Depends(require_viewer)):
    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    service = AIAssistantService()
    return service.process_message(user=_assistant_user(current_user), message=message)


@router.get("/history")
def history(current_user: AuthUser = Depends(require_viewer)):
    service = AIAssistantService()
    return {"history": [
        {"conversation_id": item.id, "title": item.title, "sport_context": item.sport_context}
        for item in service._conversations
        if item.user_id == current_user.id
    ]}


@router.delete("/conversation/{conversation_id}")
def delete_conversation(conversation_id: int):
    return {"deleted": conversation_id, "status": "ok"}
