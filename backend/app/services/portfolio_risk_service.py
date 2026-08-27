from __future__ import annotations


class PortfolioRiskService:
    def calculate(self, portfolio: dict | None) -> dict:
        portfolio = portfolio or {}
        volatility = float(portfolio.get("volatility", 30) or 30)
        drawdown = float(portfolio.get("drawdown", 12) or 12)
        loss_probability = float(portfolio.get("loss_probability", 28) or 28)
        exposure = float(portfolio.get("exposure", 38) or 38)
        concentration = float(portfolio.get("concentration", 60) or 60)
        risk_score = round((volatility + drawdown + loss_probability + exposure + concentration) / 5, 1)
        return {
            "risk_score": risk_score,
            "primary_issue": portfolio.get("primary_issue", "NBA concentration"),
            "volatility": volatility,
            "drawdown": drawdown,
            "loss_probability": loss_probability,
            "exposure": exposure,
            "concentration": concentration,
        }
