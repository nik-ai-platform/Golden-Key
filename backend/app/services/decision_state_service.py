from __future__ import annotations


class DecisionStateService:
    def build_state(self, payload: dict | None) -> dict:
        payload = payload or {}
        npi_score = float(payload.get("npi_score", 0) or 0)
        simulation_probability = float(payload.get("simulation_probability", 0) or 0)
        injuries = str(payload.get("injuries", "normal")).lower()
        rest = float(payload.get("rest", 0) or 0)
        public_betting = float(payload.get("public_betting", 50) or 50)

        confidence = "Medium"
        if npi_score >= 80 and simulation_probability >= 60 and injuries != "high":
            confidence = "High"
        elif injuries == "high" or public_betting >= 75:
            confidence = "Low"

        return {
            "state": {
                "favorite": payload.get("favorite", True),
                "strong_defense": payload.get("strong_defense", True),
                "rest_advantage": rest >= 2,
                "market_overreaction": public_betting >= 70,
            },
            "inputs": {
                "npi_score": npi_score,
                "simulation_probability": simulation_probability,
                "market_line": payload.get("market_line", "-4.5"),
                "injuries": injuries,
                "rest": rest,
                "weather": payload.get("weather", "clear"),
                "public_betting": public_betting,
                "historical_trends": payload.get("historical_trends", "stable"),
            },
            "confidence": confidence,
        }
