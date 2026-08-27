from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.agent_coordinator_service import AgentCoordinatorService
from app.services.nik_power_engine import NikPowerEngine
from app.services.portfolio_optimizer_service import PortfolioOptimizerService
from app.services.research_planner_service import ResearchPlannerService
from app.services.simulation_engine_service import SimulationEngineService


class GameServiceAdapter:
    def import_today_games(self) -> list[dict[str, Any]]:
        return [
            {"id": 101, "sport": "NFL", "home_team": "Chiefs", "away_team": "Bills"},
            {"id": 102, "sport": "NBA", "home_team": "Lakers", "away_team": "Suns"},
            {"id": 103, "sport": "NBA", "home_team": "Celtics", "away_team": "Heat"},
        ]


class TeamServiceAdapter:
    def profile(self, team_name: str) -> dict[str, Any]:
        return {
            "team": team_name,
            "form": "strong",
            "injury_pressure": "low",
        }


class OddsServiceAdapter:
    def import_odds(self, games: list[dict[str, Any]]) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for game in games:
            spread = -3 if game.get("home_team") in {"Chiefs", "Celtics"} else -1.5
            snapshots.append(
                {
                    "game_id": game["id"],
                    "spread": spread,
                    "moneyline_home": -145,
                    "moneyline_away": 125,
                    "total": 47.5 if game.get("sport") == "NFL" else 229.5,
                }
            )
        return snapshots


class NPIServiceAdapter:
    def __init__(self) -> None:
        self._engine = NikPowerEngine()

    def calculate(self, game: dict[str, Any], odds: dict[str, Any]) -> float:
        baseline = 84.0 if game.get("sport") == "NBA" else 87.0
        spread_adjustment = abs(float(odds.get("spread", 0))) * 0.8
        return round(min(99.0, baseline + spread_adjustment), 1)


class SimulationServiceAdapter:
    def __init__(self) -> None:
        self._service = SimulationEngineService()

    def run(self, game: dict[str, Any]) -> dict[str, Any]:
        return self._service.run_simulation(game, iterations=10000)


class ResearchServiceAdapter:
    def __init__(self) -> None:
        self._planner = ResearchPlannerService()

    def analyze(self, game: dict[str, Any]) -> dict[str, Any]:
        questions = self._planner.identify_questions(
            {
                "sport": game.get("sport", "NBA"),
                "accuracy_decline_pct": 4,
                "market_shift_detected": True,
            }
        )
        prioritized = self._planner.prioritize_tasks(questions)
        return {"questions": prioritized}


class PortfolioServiceAdapter:
    def __init__(self) -> None:
        self._service = PortfolioOptimizerService()

    def evaluate(self, allocation: dict[str, Any]) -> dict[str, Any]:
        return self._service.optimize(allocation)


class AgentServiceAdapter:
    def __init__(self) -> None:
        self._service = AgentCoordinatorService()

    def explain(self, game: dict[str, Any]) -> dict[str, Any]:
        result = self._service.coordinate_analysis(game)
        return {
            "recommendation": result["results"]["explanation"]["recommended"],
            "reason": result["results"]["explanation"]["reason"],
            "consensus": result["results"]["consensus"],
        }


@dataclass
class ServiceRegistry:
    game: GameServiceAdapter = GameServiceAdapter()
    team: TeamServiceAdapter = TeamServiceAdapter()
    odds: OddsServiceAdapter = OddsServiceAdapter()
    npi: NPIServiceAdapter = NPIServiceAdapter()
    simulation: SimulationServiceAdapter = SimulationServiceAdapter()
    research: ResearchServiceAdapter = ResearchServiceAdapter()
    portfolio: PortfolioServiceAdapter = PortfolioServiceAdapter()
    agent: AgentServiceAdapter = AgentServiceAdapter()
