from __future__ import annotations

from typing import Any

from app.pipeline.pipeline_context import PipelineContext
from app.services.service_registry import ServiceRegistry


class PredictionPipelineService:
    def generate(self, context: PipelineContext) -> list[dict[str, Any]]:
        registry = ServiceRegistry()
        predictions: list[dict[str, Any]] = []
        odds_lookup = {odds.get("game_id"): odds for odds in context.odds}
        npi_lookup = {item.get("game_id"): item.get("npi_score", 0) for item in context.npi_scores}

        for game, simulation in zip(context.games, context.simulations):
            game_id = game.get("id")
            odds = odds_lookup.get(game_id, {})
            npi_score = float(npi_lookup.get(game_id, 0) or 0)
            win_probability = float(simulation.get("summary", {}).get("win_probability", 50.0) or 50.0)

            ai = registry.agent.explain(game)
            risk = "high" if win_probability < 54 else "medium" if win_probability < 65 else "low"
            if risk == "high":
                recommendation = "PASS"
            else:
                recommendation = f"{game.get('home_team')} {odds.get('spread', -1.5)}"

            predictions.append(
                {
                    "game_id": game_id,
                    "market": "spread",
                    "pick": recommendation,
                    "confidence": round((npi_score + win_probability) / 2, 1),
                    "npi_score": npi_score,
                    "simulation_probability": win_probability,
                    "risk_score": risk,
                    "ai_explanation": ai.get("reason", "AI council consensus"),
                    "portfolio_rule": "max_single_game_exposure_2pct",
                }
            )

        return predictions
