from fastapi import APIRouter, Depends

from app.auth.dependencies import require_viewer
from app.services.cross_sport_analysis_service import CrossSportAnalysisService
from app.services.league_comparison_service import LeagueComparisonService
from app.services.sport_intelligence_service import SportIntelligenceService
from app.services.sport_weight_service import SportWeightService

router = APIRouter(prefix="/sports", tags=["Sports"], dependencies=[Depends(require_viewer)])


@router.get("")
def list_sports():
    service = SportIntelligenceService()
    return [
        service.get_model("NBA"),
        service.get_model("NFL"),
        service.get_model("NCAAB"),
        service.get_model("WNBA"),
    ]


@router.get("/{sport}/model")
def get_sport_model(sport: str):
    service = SportIntelligenceService()
    return service.get_model(sport)


@router.get("/{sport}/features")
def get_sport_features(sport: str):
    service = SportIntelligenceService()
    return service.get_features(sport)


@router.get("/comparison")
def get_sport_comparison():
    comparison = LeagueComparisonService()
    analysis = CrossSportAnalysisService()
    return {
        "comparison": comparison.compare([]),
        "analysis": analysis.analyze("Rest Advantage", "NBA", "+2.4% ROI", "strong", "+2.4% ROI"),
    }
