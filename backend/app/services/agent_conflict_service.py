from __future__ import annotations


class AgentConflictService:
    def detect(self, outputs: dict | None = None) -> dict:
        outputs = outputs or {}
        prediction_conf = float(outputs.get("prediction_confidence", 82) or 82)
        simulation_conf = float(outputs.get("simulation_confidence", 48) or 48)
        disagreement = abs(prediction_conf - simulation_conf)
        conflict = "HIGH" if disagreement >= 25 else "MEDIUM" if disagreement >= 12 else "LOW"
        return {
            "prediction_agent": prediction_conf,
            "simulation_agent": simulation_conf,
            "conflict": conflict,
            "reason": "Strong disagreement" if conflict == "HIGH" else "Manageable disagreement",
        }
