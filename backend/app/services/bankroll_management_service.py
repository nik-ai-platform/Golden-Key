from __future__ import annotations


class BankrollManagementService:
    def summarize(self, portfolio: dict | None) -> dict:
        portfolio = portfolio or {}
        starting = float(portfolio.get("starting_bankroll", 0) or 0)
        current = float(portfolio.get("current_balance", starting) or starting)
        exposure = float(portfolio.get("total_exposure", 0) or 0)
        exposure_pct = round((exposure / starting) * 100, 1) if starting else 0.0
        available_risk = max(0.0, round(starting * 0.25 - exposure, 2)) if starting else 0.0
        warning = "HIGH RISK" if exposure_pct > 25 else "MODERATE"
        return {
            "starting_bankroll": starting,
            "current_balance": current,
            "current_exposure": exposure_pct,
            "recommended_exposure": 25,
            "available_risk": available_risk,
            "warning": warning,
        }
