from fastapi import APIRouter, Depends

from app.auth.dependencies import require_viewer
from app.services.parlay_service import ParlayService
from app.services.correlation_service import CorrelationService
from app.services.parlay_analysis_service import ParlayAnalysisService

router = APIRouter(
    prefix="/parlays",
    tags=["Parlays"],
    dependencies=[Depends(require_viewer)],
)


@router.post("/generate")
def generate_parlays():
    service = ParlayService()
    bets = [
        {"selection": "Celtics -3.5", "probability": 0.6, "quality_score": 90},
        {"selection": "Chiefs ML", "probability": 0.65, "quality_score": 82},
    ]
    parlays = service.generate_parlays(bets, max_legs=3)
    return {"parlays": parlays}


@router.get("/top")
def top_parlays():
    service = ParlayService()
    parlays = [
        {"legs": ["Celtics -3.5", "Chiefs ML"], "probability": 39.0, "value_score": 88, "risk_score": 25},
        {"legs": ["Yankees ML"], "probability": 65.0, "value_score": 76, "risk_score": 40},
    ]
    return service.rank_parlays(parlays)


@router.get("/history")
def parlay_history():
    service = ParlayAnalysisService()
    return service.analyze([
        {"legs": ["A", "B"]},
        {"legs": ["A", "B", "C"]},
    ])


@router.get("/{parlay_id}")
def get_parlay(parlay_id: int):
    return {"id": parlay_id, "legs": 3, "probability": 42.5, "value_score": 88, "risk": "MEDIUM"}
