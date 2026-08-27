from __future__ import annotations


class AgentConsensusService:
    def combine(self, agent_outputs: dict, weights: dict | None = None) -> dict:
        weights = weights or {
            "prediction_agent": 0.25,
            "simulation_agent": 0.25,
            "research_agent": 0.25,
            "risk_agent": 0.25,
        }
        prediction_conf = float(agent_outputs.get("prediction_confidence", 78) or 78)
        simulation_conf = float(agent_outputs.get("simulation_confidence", 61) or 61)
        research_conf = float(agent_outputs.get("research_confidence", 70) or 70)
        risk_modifier = float(agent_outputs.get("risk_modifier", -4) or -4)
        confidence = round(
            prediction_conf * weights.get("prediction_agent", 0.25)
            + simulation_conf * weights.get("simulation_agent", 0.25)
            + research_conf * weights.get("research_agent", 0.25)
            + (70 + risk_modifier) * weights.get("risk_agent", 0.25),
            1,
        )
        return {
            "final_pick": agent_outputs.get("final_pick", "Celtics -4"),
            "confidence": confidence,
            "summary": {
                "prediction": prediction_conf,
                "simulation": simulation_conf,
                "research": "Positive",
                "risk": "Moderate",
            },
        }
