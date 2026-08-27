from app.services.bankroll_management_service import BankrollManagementService
from app.services.bet_correlation_service import BetCorrelationService
from app.services.hedge_analysis_service import HedgeAnalysisService
from app.services.performance_attribution_service import PerformanceAttributionService
from app.services.portfolio_coach_service import PortfolioCoachService
from app.services.portfolio_optimizer_service import PortfolioOptimizerService
from app.services.portfolio_risk_service import PortfolioRiskService
from app.services.portfolio_simulation_service import PortfolioSimulationService
from app.services.position_sizing_service import PositionSizingService


def test_account_creation_and_bankroll_calculations():
    service = BankrollManagementService()

    summary = service.summarize({"starting_bankroll": 5000, "current_balance": 5425, "total_exposure": 1900})

    assert summary["current_balance"] == 5425
    assert summary["warning"] == "HIGH RISK"


def test_position_tracking_and_sizing_logic():
    service = PositionSizingService()

    fixed = service.fixed_unit(5000, 1.0)
    fractional = service.fractional_kelly(82, -110)
    risk_adjusted = service.risk_adjusted_sizing(5000, 82, -110, "moderate")

    assert fixed["stake"] == 50.0
    assert fractional["stake_percent"] > 0
    assert risk_adjusted["recommended_stake_percent"] > 0


def test_risk_scoring_and_allocation_logic():
    optimizer = PortfolioOptimizerService()
    risk_service = PortfolioRiskService()

    optimized = optimizer.optimize({"NBA": 60, "NFL": 30, "NCAAB": 10})
    risk = risk_service.calculate({"volatility": 32, "drawdown": 11, "loss_probability": 28, "exposure": 38, "concentration": 61})

    assert "diversification" in optimized["recommendation"].lower()
    assert risk["risk_score"] == 34.0


def test_correlation_detection_and_hedge_analysis():
    correlation = BetCorrelationService().detect([
        {"market": "Chiefs ML"},
        {"market": "Chiefs Spread"},
        {"market": "Chiefs Over"},
    ])
    hedge = HedgeAnalysisService().analyze({"market": "Lakers ML"})

    assert correlation["high_correlation"] is True
    assert hedge["potential_hedge"] == "Warriors +6"


def test_simulation_results_and_ai_coaching():
    simulation = PortfolioSimulationService().simulate({"current_balance": 5425})
    coach = PortfolioCoachService().review({"strength": "NBA ATS", "weakness": "Overexposure to favorites"})

    assert simulation["median"] == 7275.0
    assert coach["recommendation"] == "Increase diversification"


def test_performance_attribution_identifies_profit_source():
    attribution = PerformanceAttributionService().explain({"profit_source": "NBA Underdogs", "contribution": "+72% of ROI"})

    assert attribution["profit_source"] == "NBA Underdogs"
    assert attribution["contribution"] == "+72% of ROI"
