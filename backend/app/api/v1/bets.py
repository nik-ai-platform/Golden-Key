from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.auth.dependencies import require_viewer
from app.database.session import get_db
from app.services.betting_strategy_service import BettingStrategyService
from app.services.market_conflict_detector import MarketConflictDetector
from app.services.parlay_compatibility_service import ParlayCompatibilityService
from app.services.risk_service import RiskService

router = APIRouter(
    prefix="/bets",
    tags=["Bets"],
    dependencies=[Depends(require_viewer)],
)


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    service = BettingStrategyService()
    return [
        {
            "game": "DAL vs PHX",
            "recommendation": "STRONG_BET",
            "selection": "DAL +5",
            "quality_score": 86,
            "risk": "LOW",
            "value_score": service.evaluate_bet(6, 5, 84)["value_score"],
        }
    ]


@router.get("/top")
def get_top_recommendations():
    service = BettingStrategyService()
    result = service.evaluate_bet(6, 4, 88)
    return {
        "game": "BOS vs CLE",
        "selection": "BOS ML",
        "quality_score": result["quality_score"],
        "recommendation": result["recommendation"],
        "risk": "LOW",
    }


@router.get("/{game_id}")
def get_bet_by_game(game_id: int):
    return {
        "game_id": game_id,
        "recommendation": "STRONG_BET",
        "selection": "DAL +5",
        "quality_score": 86,
        "risk": "LOW",
    }


@router.get("/risk")
def get_risk():
    service = RiskService()
    return service.calculate_risk(
        {
            "uncertainty": "LOW",
            "market_agreement": "STRONG",
            "sample_size": "MEDIUM",
            "injury_uncertainty": False,
        }
    )


@router.get("/conflicts")
def get_conflicts():
    detector = MarketConflictDetector()
    return detector.detect_conflict(model_line=8, market_line=2)


@router.get("/parlay-compatibility")
def get_parlay_compatibility():
    service = ParlayCompatibilityService()
    return service.calculate_compatibility_score(
        {"game_id": 1, "selection": "DAL +5"},
        {"game_id": 2, "selection": "BOS ML"},
    )
