from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.ai_research_agent_service import AIResearchAgentService
from app.services.prediction_engine import PredictionEngine
from app.services.sports_intelligence_core_service import (
    SportsIntelligenceCoreService,
)
from app.services.sports_reasoning_service import SportsReasoningService

router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence"],
)

engine = PredictionEngine()
intelligence_core = SportsIntelligenceCoreService()
reasoning_service = SportsReasoningService()
research_service = AIResearchAgentService()


def analyze(payload: dict):
    question = str(payload.get("question", ""))
    return {
        "analysis": intelligence_core.analyze(question),
        "persona": "Golden Key Sports Intelligence",
        "context": payload.get("context", {}),
    }


def explain(payload: dict):
    analysis = analyze(payload)
    reasoning = reasoning_service.explain(payload)
    return {
        "explanation": reasoning["explanation"],
        "analysis": analysis["analysis"],
    }


def research():
    objective = research_service.analyze_objective(
        "Discover repeatable sports market edges"
    )
    return {
        "plan": research_service.generate_hypotheses(objective),
    }


def compare(payload: dict):
    return {
        "matchup": (
            f"{payload.get('team_a', 'Team A')} vs "
            f"{payload.get('team_b', 'Team B')}"
        ),
        "analysis": intelligence_core.analyze(
            str(payload.get("question", "Compare this matchup"))
        ),
    }


def strategy(payload: dict):
    objective = research_service.analyze_objective(
        str(payload.get("objective", "Improve model performance"))
    )
    return {
        "actions": research_service.generate_hypotheses(objective),
        "objective": objective,
    }


def today_intelligence():
    return {
        "top_pick": "Best available model edge",
        "confidence": 0.78,
    }


def game_intelligence(game_id: int):
    return {
        "game_id": game_id,
        "prediction": "Analysis available",
    }


def top_picks():
    return {"picks": []}


def intelligence_reports():
    return {"reports": []}


@router.post("/analyze/{game_id}")
def analyze_game(
    game_id: int,
    db: Session = Depends(get_db),
):
    return engine.analyze_game(
        db,
        game_id,
    )
