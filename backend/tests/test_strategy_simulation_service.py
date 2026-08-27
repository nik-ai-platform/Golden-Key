from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.services.strategy_simulation_service import StrategySimulationService
from app.services.historical_replay_service import HistoricalReplayService
from app.services.bankroll_simulation_service import BankrollSimulationService
from app.services.strategy_risk_service import StrategyRiskService
from app.services.strategy_comparison_service import StrategyComparisonService
from app.services.monte_carlo_service import MonteCarloService


def test_strategies_save_correctly():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        service = StrategySimulationService()
        strategy = service.save_strategy(
            db,
            {
                "user_id": 1,
                "strategy_name": "NBA Conservative ATS",
                "sport": "NBA",
                "market_type": "ATS",
                "rules": {"confidence_threshold": 75, "minimum_edge": 3, "parlay_rules": "single"},
                "starting_bankroll": 5000,
            },
        )
        assert strategy.strategy_name == "NBA Conservative ATS"
    finally:
        db.close()


def test_historical_replay_works():
    service = HistoricalReplayService()
    result = service.replay({"sport": "NBA", "market": "ATS"}, [{"outcome": "win"}, {"outcome": "loss"}])
    assert result["games_replayed"] == 2


def test_bankroll_calculations_correct():
    service = BankrollSimulationService()
    result = service.simulate(5000, [{"bet_size": 100, "win": True, "payout": 180}, {"bet_size": 100, "win": False, "payout": 0}])
    assert result["ending_bankroll"] == 5080


def test_risk_scores_accurate():
    service = StrategyRiskService()
    result = service.score({"volatility": "low", "variance": 0.08, "downside_risk": 0.12, "losing_streak_probability": 0.2, "sample_size": 120})
    assert result["risk"] == "LOW"


def test_simulations_reproducible():
    service = MonteCarloService()
    result = service.run(1000)
    assert result["simulations"] == 1000


def test_user_restrictions_respected():
    service = StrategySimulationService()
    strategy = {"strategy_name": "Aggressive", "sport": "NBA", "market_type": "ATS"}
    profile = {"risk_level": "CONSERVATIVE"}
    result = service.check_user_restrictions(strategy, profile)
    assert result["allowed"] is False
