from __future__ import annotations


class AgentDebateService:
    def run(self, opinions: dict) -> dict:
        prediction = opinions.get("prediction_agent", "Celtics -4")
        risk = opinions.get("risk_agent", "PASS")
        simulation = opinions.get("simulation_agent", "Celtics probability: 61%")
        prompt = "Does edge justify risk?"
        return {
            "prediction_agent": prediction,
            "risk_agent": risk,
            "simulation_agent": simulation,
            "debate": prompt,
        }
