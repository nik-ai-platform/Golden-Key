from __future__ import annotations


class RiskAgent:
    name = "risk_agent"

    def analyze(self, game: dict) -> dict:
        return {
            "risk": "Medium",
            "concern": "High public ownership",
            "factors": ["Volatility", "Correlation", "Uncertainty", "Market Risk"],
            "game": game,
        }
