from fastapi import APIRouter, Depends

from app.auth.dependencies import require_owner_or_admin, require_viewer
from app.auth.schemas import AuthUser
from app.services.bet_correlation_service import BetCorrelationService
from app.services.bet_management_service import BetManagementService
from app.services.exposure_service import ExposureService
from app.services.performance_attribution_service import PerformanceAttributionService
from app.services.portfolio_bankroll_service import PortfolioBankrollService
from app.services.portfolio_coach_service import PortfolioCoachService
from app.services.portfolio_health_service import PortfolioHealthService
from app.services.portfolio_optimizer_service import PortfolioOptimizerService
from app.services.portfolio_risk_service import PortfolioRiskService
from app.services.portfolio_simulation_service import PortfolioSimulationService
from app.services.bankroll_management_service import BankrollManagementService
from app.services.position_sizing_service import PositionSizingService
from app.services.hedge_analysis_service import HedgeAnalysisService
from app.services.bet_settlement_service import BetSettlementService

router = APIRouter(prefix="/portfolio", tags=["Portfolio"], dependencies=[Depends(require_viewer)])


def _portfolio_payload(user_id: int) -> dict:
    portfolio = {
        "id": 1,
        "user_id": user_id,
        "name": "Main NBA Portfolio",
        "starting_bankroll": 5000,
        "current_balance": 5425,
        "current_bankroll": 5625,
        "total_exposure": 600,
        "risk_profile": "moderate",
        "risk_level": "MODERATE",
    }
    portfolio.update(BankrollManagementService().summarize(portfolio))
    return portfolio


@router.post("")
def create_portfolio(payload: dict):
    return {
        "id": 1,
        "user_id": payload.get("user_id", 1),
        "name": payload.get("name", "Main NBA Portfolio"),
        "starting_bankroll": payload.get("starting_bankroll", 5000),
        "current_bankroll": payload.get("current_bankroll", 5625),
        "total_exposure": payload.get("total_exposure", 600),
        "risk_level": payload.get("risk_level", "MODERATE"),
    }


@router.get("")
def get_portfolio(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    return _portfolio_payload(user_id)


@router.post("/position")
def create_position(payload: dict):
    sizing = PositionSizingService().risk_adjusted_sizing(
        bankroll=payload.get("bankroll", 5000),
        confidence=payload.get("confidence", 80),
        odds=payload.get("odds", -110),
        risk_profile=payload.get("risk_profile", "moderate"),
    )
    return {
        "portfolio_id": payload.get("portfolio_id", 1),
        "game_id": payload.get("game_id", 1),
        "market": payload.get("market", "NBA Celtics -4"),
        "stake": payload.get("stake", round(float(payload.get("bankroll", 5000)) * (sizing["recommended_stake_percent"] / 100.0), 2)),
        "odds": payload.get("odds", -110),
        "confidence": payload.get("confidence", 84),
        "status": "open",
        "result": None,
    }


@router.post("/bets")
def create_bet(payload: dict):
    service = BetManagementService()
    return service.create_bet(payload)


@router.get("/bets/open")
def get_open_bets(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    service = BetManagementService()
    return service.get_active_bets(user_id)


@router.put("/bets/{bet_id}/result")
def update_bet_result(bet_id: int, payload: dict):
    service = BetManagementService()
    result = service.update_bet_result(bet_id)
    settlement = BetSettlementService().settle_bet({"stake": payload.get("stake", 100), "odds": payload.get("odds", 1.9)}, payload.get("result", "WIN"))
    result.update(settlement)
    return result


@router.get("/health")
def get_portfolio_health():
    service = PortfolioHealthService()
    return service.score({"risk_score": 20, "diversification_score": 85, "bankroll_discipline": 80, "expected_value": 75, "drawdown": 4})


@router.get("/performance")
def get_portfolio_performance():
    service = PerformanceAttributionService()
    return service.explain({"profit_driver": "NBA ATS", "loss_driver": "NFL Parlays", "best_strategy": "High-confidence singles"})


@router.get("/risk")
def get_portfolio_risk(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    portfolio = _portfolio_payload(user_id)
    risk = PortfolioRiskService().calculate({"volatility": 32, "drawdown": 11, "loss_probability": 28, "exposure": 38, "concentration": 61})
    return {"portfolio": portfolio, "risk": risk}


@router.get("/simulation")
def get_portfolio_simulation(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    portfolio = _portfolio_payload(user_id)
    simulation = PortfolioSimulationService().simulate(portfolio)
    return {"portfolio": portfolio, "simulation": simulation}


@router.get("/recommendations")
def get_portfolio_recommendations(user_id: int, current_user: AuthUser = Depends(require_viewer)):
    require_owner_or_admin(user_id, current_user)
    portfolio = _portfolio_payload(user_id)
    optimizer = PortfolioOptimizerService().optimize({"NBA": 60, "NFL": 30, "NCAAB": 10})
    correlation = BetCorrelationService().detect([
        {"market": "Chiefs ML"},
        {"market": "Chiefs Spread"},
        {"market": "Chiefs Over"},
    ])
    hedge = HedgeAnalysisService().analyze({"market": "Lakers ML"})
    coach = PortfolioCoachService().review({"strength": "NBA ATS", "weakness": "Overexposure to favorites"})
    return {"portfolio": portfolio, "optimizer": optimizer, "correlation": correlation, "hedge": hedge, "coach": coach}
