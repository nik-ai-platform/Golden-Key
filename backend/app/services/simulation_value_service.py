from __future__ import annotations


class SimulationValueService:
    def find_value(self, simulation_probability: float, market_probability: float) -> dict[str, float | str]:
        edge = round(simulation_probability - market_probability, 1)
        recommendation = "VALUE FOUND" if edge >= 5 else "NO VALUE"
        return {
            "simulation_probability": simulation_probability,
            "market_probability": market_probability,
            "edge": edge,
            "recommendation": recommendation,
        }
