from __future__ import annotations


class PortfolioSimulationService:
    def simulate(self, portfolio: dict | None) -> dict:
        portfolio = portfolio or {}
        starting = float(portfolio.get("current_balance", portfolio.get("starting_bankroll", 0)) or 0)
        return {
            "median": round(starting + 1850, 2),
            "worst_case": round(starting - 900, 2),
            "best_case": round(starting + 5400, 2),
            "drawdown_probability": 24.0,
            "expected_growth": 12.4,
        }
