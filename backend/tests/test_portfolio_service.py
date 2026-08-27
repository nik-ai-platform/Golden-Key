from app.services.bet_management_service import BetManagementService
from app.services.exposure_service import ExposureService
from app.services.portfolio_health_service import PortfolioHealthService
from app.services.bet_settlement_service import BetSettlementService


def test_bets_save_correctly_and_exposure_calculates():
    service = BetManagementService()
    bet = service.create_bet({"portfolio_id": 1, "sport": "NBA", "market": "ATS", "selection": "Boston -3.5", "stake": 100, "confidence": 82, "status": "OPEN"})
    assert bet["status"] == "OPEN"

    exposure_service = ExposureService()
    portfolio = {"daily_risk": 800, "daily_limit": 1000, "sport_exposure": {"NBA": 800}, "team_exposure": {"Celtics": 800}}
    exposure = exposure_service.calculate_exposure(portfolio)
    assert exposure["status"] == "Allowed"
    assert exposure["team_exposure"]["Celtics"] == 800


def test_settlement_and_health_score_work():
    settlement = BetSettlementService().settle_bet({"stake": 100, "odds": 1.9}, "WIN")
    assert settlement["result"] == "WIN"
    assert settlement["net"] == 90.0

    health = PortfolioHealthService().score({"risk_score": 20, "diversification_score": 85, "bankroll_discipline": 80, "expected_value": 75, "drawdown": 4})
    assert health["score"] >= 80
