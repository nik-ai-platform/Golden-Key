from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst, require_viewer
from app.database.session import get_db
from app.services.strategy_simulation_service import StrategySimulationService
from app.services.strategy_comparison_service import StrategyComparisonService
from app.services.historical_replay_service import HistoricalReplayService
from app.services.monte_carlo_service import MonteCarloService

router = APIRouter(prefix="/strategies", tags=["Strategies"], dependencies=[Depends(require_viewer)])


@router.post("")
def create_strategy(payload: dict, db: Session = Depends(get_db), _=Depends(require_analyst)):
    service = StrategySimulationService()
    return service.save_strategy(db, payload)


@router.get("")
def list_strategies():
    return [{"strategy_name": "NBA Conservative ATS", "sport": "NBA"}]


@router.post("/simulate")
def simulate_strategy(payload: dict, _=Depends(require_analyst)):
    service = StrategySimulationService()
    replay = HistoricalReplayService()
    simulation = service.run_simulation(payload.get("strategy"), payload.get("historical_games"))
    replay_result = replay.replay(payload.get("strategy"), payload.get("historical_games"))
    return {"simulation": simulation, "replay": replay_result}


@router.get("/results/{strategy_id}")
def get_results(strategy_id: int):
    return {"strategy_id": strategy_id, "roi": 14.2, "risk": "LOW"}


@router.post("/compare")
def compare_strategies(payload: dict, _=Depends(require_analyst)):
    service = StrategyComparisonService()
    return service.compare(payload.get("strategy_a"), payload.get("strategy_b"))


@router.post("/monte-carlo")
def run_monte_carlo(payload: dict, _=Depends(require_analyst)):
    service = MonteCarloService()
    return service.run(payload.get("simulations", 1000))
