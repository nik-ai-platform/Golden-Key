from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.models.ai_agent import AIAgent
from app.services.agent_coordinator_service import AgentCoordinatorService

router = APIRouter(prefix="/agents", tags=["Multi Agent"], dependencies=[Depends(require_analyst)])

_AGENTS = [
    AIAgent(name="Prediction Agent", agent_type="prediction", version="1.0", status="active", performance_score=58.4),
    AIAgent(name="Research Agent", agent_type="research", version="1.0", status="active", performance_score=57.1),
    AIAgent(name="Simulation Agent", agent_type="simulation", version="1.0", status="active", performance_score=59.2),
    AIAgent(name="Risk Agent", agent_type="risk", version="1.0", status="active", performance_score=58.8),
]
_COORDINATOR = AgentCoordinatorService()


@router.post("/analyze")
def analyze(payload: dict):
    return _COORDINATOR.coordinate_analysis(payload)


@router.get("")
def list_agents():
    return [
        {
            "name": agent.name,
            "agent_type": agent.agent_type,
            "version": agent.version,
            "status": agent.status,
            "performance_score": agent.performance_score,
        }
        for agent in _AGENTS
    ]


@router.get("/debate")
def get_debate():
    return _COORDINATOR.collect_results(_COORDINATOR.assign_task({"game": "Chiefs vs Bills"}))["debate"]


@router.get("/consensus")
def get_consensus():
    return _COORDINATOR.collect_results(_COORDINATOR.assign_task({"game": "Celtics vs Lakers"}))["consensus"]


@router.get("/performance")
def get_performance():
    results = _COORDINATOR.collect_results(_COORDINATOR.assign_task({"game": "Lakers vs Celtics"}))
    return {
        "consensus_accuracy": 58.9,
        "active_agents": 7,
        "current_debate": "Chiefs vs Bills",
        "agent_reputation": results["reputation"],
    }
