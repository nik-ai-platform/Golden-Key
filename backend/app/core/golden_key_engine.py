from __future__ import annotations

from typing import Any

from app.services.service_registry import ServiceRegistry


class GoldenKeyEngine:
    def __init__(self, registry: ServiceRegistry | None = None) -> None:
        self.registry = registry or ServiceRegistry()

    def analyze_game(self, game_id: int) -> dict[str, Any]:
        games = self.registry.game.import_today_games()
        game = next((item for item in games if int(item.get("id", -1)) == game_id), games[0])
        prediction = self.generate_prediction(game)
        intelligence = self.run_intelligence(game)
        return {
            "game": game,
            "prediction": prediction,
            "intelligence": intelligence,
        }

    def generate_prediction(self, game: dict[str, Any]) -> dict[str, Any]:
        odds = self.registry.odds.import_odds([game])[0]
        npi_score = self.registry.npi.calculate(game, odds)
        simulation = self.registry.simulation.run(game)
        win_probability = float(simulation["summary"].get("win_probability", 50.0))
        confidence = round((npi_score + win_probability) / 2, 1)
        pick = f"{game['home_team']} {odds['spread']}"
        risk = "low" if confidence >= 78 else "medium" if confidence >= 62 else "high"

        return {
            "game_id": game["id"],
            "pick": pick,
            "market": "spread",
            "confidence": confidence,
            "npi_score": npi_score,
            "simulation_probability": win_probability,
            "risk_score": risk,
            "model_version": "NPI-v1",
        }

    def run_intelligence(self, game: dict[str, Any]) -> dict[str, Any]:
        ai = self.registry.agent.explain(game)
        research = self.registry.research.analyze(game)
        portfolio = self.registry.portfolio.evaluate(
            {
                "NBA": 55,
                "NFL": 30,
                "NCAAB": 15,
            }
        )
        return {
            "ai": ai,
            "research": research,
            "portfolio": portfolio,
        }

    def create_report(self, result: dict[str, Any]) -> dict[str, Any]:
        prediction = result.get("prediction", {})
        game = result.get("game", {})
        summary = (
            f"{game.get('home_team', 'Home')} vs {game.get('away_team', 'Away')}: "
            f"{prediction.get('pick', 'N/A')} at {prediction.get('confidence', 0)} confidence"
        )
        return {
            "summary": summary,
            "result": result,
            "reason": "Defense + Rest + Simulation Edge",
        }
