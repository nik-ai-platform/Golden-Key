from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_analyst
from app.services.game_monte_carlo_service import GameMonteCarloService
from app.services.game_scenario_service import GameScenarioService
from app.services.simulation_engine_service import SimulationEngineService
from app.services.simulation_value_service import SimulationValueService
from app.services.simulation_explanation_service import SimulationExplanationService

router = APIRouter(prefix="/simulation", tags=["Simulation"], dependencies=[Depends(require_analyst)])

_engine_service = SimulationEngineService()
_scenario_service = GameScenarioService()
_value_service = SimulationValueService()
_explanation_service = SimulationExplanationService()
_monte_carlo_service = GameMonteCarloService()

_results_store: dict[int, dict] = {}
_next_id = 1


@router.post("/run")
def run_simulation(payload: dict):
    global _next_id

    game = payload.get("game") or {}
    iterations = int(payload.get("iterations", 10000))
    if not game:
        raise HTTPException(status_code=400, detail="game is required")

    result = _engine_service.run_simulation(game, iterations)
    monte_carlo = _monte_carlo_service.run(game, iterations)
    explanation = _explanation_service.explain({"win_probability": result["summary"]["win_probability"]})

    simulation_id = _next_id
    _next_id += 1
    _results_store[simulation_id] = {
        "id": simulation_id,
        "game": game,
        "iterations": iterations,
        "result": result,
        "monte_carlo": monte_carlo,
        "explanation": explanation,
    }

    return _results_store[simulation_id]


@router.get("/results/{simulation_id}")
def get_results(simulation_id: int):
    result = _results_store.get(simulation_id)
    if not result:
        raise HTTPException(status_code=404, detail="simulation not found")
    return result


@router.post("/scenario")
def run_scenario(payload: dict):
    return _scenario_service.simulate(payload)


@router.get("/value")
def get_value(simulation_probability: float = 62.0, market_probability: float = 52.0):
    return _value_service.find_value(simulation_probability, market_probability)
