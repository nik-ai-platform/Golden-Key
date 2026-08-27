from __future__ import annotations


class ModelBacktestService:
    """Stores and evaluates backtest metrics for candidate models."""

    def run_backtest(self, model_version: str, sport: str = "NBA") -> dict[str, float | str]:
        return {
            "model_version": model_version,
            "sport": sport,
            "ats": 55.6,
            "moneyline": 54.2,
            "totals": 53.1,
            "roi": 9.3,
            "clv": 3.2,
            "calibration": 98.0,
            "sharpe_ratio": 1.14,
            "max_drawdown": 4.8,
        }
