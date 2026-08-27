from app.services.adaptive_recommendation_service import AdaptiveRecommendationService
from app.services.confidence_adjustment_service import ConfidenceAdjustmentService
from app.services.decision_agent_service import DecisionAgentService
from app.services.decision_state_service import DecisionStateService
from app.services.policy_management_service import PolicyManagementService
from app.services.reward_engine_service import RewardEngineService
from app.services.risk_decision_service import RiskDecisionService
from app.services.strategy_selection_service import StrategySelectionService


def test_state_generation_works():
    state = DecisionStateService().build_state({"npi_score": 81, "simulation_probability": 63, "rest": 2, "public_betting": 68})

    assert state["confidence"] in {"High", "Medium", "Low"}
    assert state["state"]["rest_advantage"] is True


def test_reward_calculation_and_agent_decision_work():
    reward = RewardEngineService().calculate_reward({
        "correct_prediction": True,
        "roi_improvement": 0.5,
        "risk_reduction": 0.4,
        "confidence_accuracy": 0.7,
        "long_term_stability": 0.6,
    })
    agent = DecisionAgentService()
    options = agent.evaluate_options({"confidence": "Medium"})
    decision = agent.choose_action(options)

    assert reward["reward"] > 0
    assert decision["action"]


def test_strategy_selection_and_confidence_adjustment_work():
    strategy = StrategySelectionService().select({"sport": "NBA"})
    confidence = ConfidenceAdjustmentService().adjust({"confidence": 85, "volatility": 0.9, "model_health": "degraded", "sample_size": 80})

    assert strategy["selected_approach"] == "Hybrid NPI + Simulation"
    assert confidence["adjusted"] < confidence["before"]


def test_risk_filtering_and_adaptive_recommendation_work():
    risk = RiskDecisionService().evaluate({"portfolio_exposure": 0.6, "correlation": 0.7, "volatility": 0.65, "downside_risk": 0.6})
    recommendation = AdaptiveRecommendationService().recommend({"edge": 1.0, "uncertainty": 0.75})

    assert risk["action"] == "Reduce position"
    assert recommendation["final_recommendation"] == "PASS"


def test_memory_policy_and_policy_updates_work():
    policy = PolicyManagementService()

    snapshot = policy.snapshot()
    updated = policy.update("Better injury weighting", approved=True)

    assert snapshot["agent_version"] == "v1.8"
    assert updated["agent_version"] == "v2.1"
