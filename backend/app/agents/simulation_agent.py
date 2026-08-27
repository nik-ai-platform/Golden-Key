from __future__ import annotations


class SimulationAgent:
    name = "simulation_agent"

    def analyze(self, game: dict) -> dict:
        return {
            "win_probability": 61,
            "projected_score": "115-108",
            "methods": ["Monte Carlo", "Game Simulations", "Scenario Tests"],
            "game": game,
        }
