from __future__ import annotations


class PortfolioAgent:
    name = "portfolio_agent"

    def analyze(self, game: dict) -> dict:
        return {
            "portfolio_action": "reduce_position",
            "reason": "existing correlated exposure",
            "game": game,
        }
