from __future__ import annotations

from typing import Any


class RiskIntelligenceService:
    def analyze(self, bankroll: float, bet_size: float, exposure: float, variance: float, loss_streaks: int, market_risk: float) -> dict[str, Any]:
        ratio = (bet_size / bankroll) if bankroll else 0
        warning = ratio > 0.025 or exposure > 0.25 or loss_streaks >= 3 or market_risk > 0.4
        return {
            "bankroll": bankroll,
            "bet_size": bet_size,
            "exposure": exposure,
            "variance": variance,
            "loss_streaks": loss_streaks,
            "market_risk": market_risk,
            "warning": warning,
            "recommended_limit": "<25%" if exposure > 0.25 else "within target",
        }
