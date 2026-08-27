from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.services.ai_analyst_service import AIAnalystService
from app.services.daily_report_service import DailyReportService

router = APIRouter(
    prefix="/analyst",
    tags=["Analyst"],
    dependencies=[Depends(require_analyst)],
)


@router.get("/game/{game_id}")
def get_game_analysis(game_id: int):
    service = AIAnalystService()
    return service.generate_analysis(game_id)


@router.get("/daily-report")
def get_daily_report():
    service = DailyReportService()
    return service.generate_report()


@router.post("/question")
def ask_question(payload: dict):
    service = AIAnalystService()
    return service.answer_question(payload.get("question", ""), payload.get("context", {}))
