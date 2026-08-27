from __future__ import annotations


class AgentWeightingService:
    def update(self, performance: dict | None = None) -> dict:
        performance = performance or {}
        sim = float(performance.get("simulation_agent", 0.35) or 0.35)
        risk = float(performance.get("risk_agent", 0.30) or 0.30)
        pred = float(performance.get("prediction_agent", 0.20) or 0.20)
        research = float(performance.get("research_agent", 0.15) or 0.15)
        return {
            "weights": {
                "simulation_agent": sim,
                "risk_agent": risk,
                "prediction_agent": pred,
                "research_agent": research,
            }
        }
