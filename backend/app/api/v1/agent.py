from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.models.agent_memory import AgentMemory
from app.models.learning_environment import LearningEnvironment
from app.services.adaptive_recommendation_service import AdaptiveRecommendationService
from app.services.confidence_adjustment_service import ConfidenceAdjustmentService
from app.services.decision_agent_service import DecisionAgentService
from app.services.decision_state_service import DecisionStateService
from app.services.policy_management_service import PolicyManagementService
from app.services.reward_engine_service import RewardEngineService
from app.services.risk_decision_service import RiskDecisionService
from app.services.strategy_selection_service import StrategySelectionService

router = APIRouter(prefix="/agent", tags=["Reinforcement Learning"], dependencies=[Depends(require_analyst)])

decision_state_service = DecisionStateService()
reward_engine_service = RewardEngineService()
decision_agent_service = DecisionAgentService()
strategy_selection_service = StrategySelectionService()
confidence_service = ConfidenceAdjustmentService()
risk_service = RiskDecisionService()
policy_service = PolicyManagementService()
adaptive_service = AdaptiveRecommendationService()

MEMORY: list[dict] = []


@router.post("/state")
def create_state(payload: dict):
    state = decision_state_service.build_state(payload)
    environment = LearningEnvironment(
        sport=payload.get("sport", "NBA"),
        market_type=payload.get("market_type", "ATS"),
        team_context=str(payload.get("team_context", {})),
        market_conditions=str(payload.get("market_conditions", {})),
        environment_state=str(state["state"]),
    )
    return {
        "sport": environment.sport,
        "market_type": environment.market_type,
        "environment_state": state,
    }


@router.post("/decision")
def make_decision(payload: dict):
    state = decision_state_service.build_state(payload)
    options = decision_agent_service.evaluate_options(state)
    action = decision_agent_service.choose_action(options)
    strategy = strategy_selection_service.select(state)
    confidence = confidence_service.adjust({
        "confidence": payload.get("confidence", 85),
        "volatility": payload.get("volatility", 0.7),
        "model_health": payload.get("model_health", "healthy"),
        "sample_size": payload.get("sample_size", 300),
    })
    risk = risk_service.evaluate(payload)
    recommendation = adaptive_service.recommend({"edge": payload.get("edge", 1.2), "uncertainty": payload.get("uncertainty", 0.7)})
    return {
        "state": state,
        "options": options,
        "decision": action,
        "strategy": strategy,
        "confidence": confidence,
        "risk": risk,
        "recommendation": recommendation,
    }


@router.post("/rewards")
def calculate_rewards(payload: dict):
    reward = reward_engine_service.calculate_reward(payload)
    policy_update = decision_agent_service.update_policy(reward["reward"])
    return {"reward": reward, "policy_update": policy_update}


@router.get("/memory")
def list_memory():
    return {"memory": MEMORY}


@router.post("/memory")
def create_memory(payload: dict):
    memory_row = AgentMemory(
        decision=payload.get("decision", "Avoid"),
        environment=str(payload.get("environment", {})),
        outcome=str(payload.get("outcome", "Unknown")),
        reward=str(payload.get("reward", "0")),
        lesson_learned=payload.get("lesson_learned", "Reduced confidence improves results"),
    )
    record = {
        "id": len(MEMORY) + 1,
        "decision": memory_row.decision,
        "environment": memory_row.environment,
        "outcome": memory_row.outcome,
        "reward": memory_row.reward,
        "lesson_learned": memory_row.lesson_learned,
    }
    MEMORY.append(record)
    return record


@router.get("/policy")
def get_policy():
    return policy_service.snapshot()


@router.post("/policy")
def update_policy(payload: dict):
    return policy_service.update(payload.get("change", "Better injury weighting"), approved=payload.get("approved", False))
