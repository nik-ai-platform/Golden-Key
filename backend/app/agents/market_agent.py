from __future__ import annotations


class MarketAgent:
    name = "market_agent"

    def analyze(self, game: dict) -> dict:
        return {
            "line_value": "+0.8",
            "market_bias": "favorite inflation",
            "game": game,
        }
