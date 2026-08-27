from __future__ import annotations


class StrategySelectionService:
    def select(self, environment: dict | None = None) -> dict:
        environment = environment or {}
        choices = [
            {"name": "NPI Model", "historical_performance": 0.62, "risk": 0.35, "confidence": 0.7},
            {"name": "Simulation Model", "historical_performance": 0.64, "risk": 0.33, "confidence": 0.72},
            {"name": "Market Model", "historical_performance": 0.57, "risk": 0.4, "confidence": 0.61},
            {"name": "Community Consensus", "historical_performance": 0.55, "risk": 0.45, "confidence": 0.58},
            {"name": "Hybrid NPI + Simulation", "historical_performance": 0.68, "risk": 0.32, "confidence": 0.76},
        ]
        selected = max(choices, key=lambda item: item["historical_performance"])
        return {
            "selected_approach": selected["name"],
            "reason": "Highest historical performance",
            "environment": environment,
        }
