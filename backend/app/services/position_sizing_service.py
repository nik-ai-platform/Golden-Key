from __future__ import annotations


class PositionSizingService:
    def fixed_unit(self, bankroll: float, unit_percent: float = 1.0) -> dict:
        stake = round(float(bankroll or 0) * (float(unit_percent) / 100.0), 2)
        return {"stake": stake, "method": "fixed_unit"}

    def kelly_criterion(self, confidence: float, odds: float) -> float:
        win_prob = max(0.0, min(1.0, float(confidence) / 100.0))
        decimal_odds = 1 + (100 / abs(float(odds))) if odds < 0 else 1 + (float(odds) / 100)
        b = decimal_odds - 1
        q = 1 - win_prob
        fraction = (b * win_prob - q) / b if b else 0.0
        return max(0.0, round(fraction * 100, 2))

    def fractional_kelly(self, confidence: float, odds: float, fraction: float = 0.5) -> dict:
        return {"stake_percent": round(self.kelly_criterion(confidence, odds) * float(fraction), 2), "method": "fractional_kelly"}

    def risk_adjusted_sizing(self, bankroll: float, confidence: float, odds: float, risk_profile: str | None = None) -> dict:
        base = self.kelly_criterion(confidence, odds)
        multiplier = 0.75 if (risk_profile or "").lower() == "conservative" else 1.0 if (risk_profile or "").lower() == "moderate" else 1.15
        return {"recommended_stake_percent": round(base * multiplier, 2), "bankroll": bankroll, "method": "risk_adjusted"}
