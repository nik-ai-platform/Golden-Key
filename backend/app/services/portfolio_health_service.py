class PortfolioHealthService:
    def score(self, portfolio):
        portfolio = portfolio or {}
        risk_score = float(portfolio.get("risk_score", 20) or 20)
        diversification_score = float(portfolio.get("diversification_score", 85) or 85)
        bankroll_discipline = float(portfolio.get("bankroll_discipline", 80) or 80)
        expected_value = float(portfolio.get("expected_value", 75) or 75)
        drawdown = float(portfolio.get("drawdown", 4) or 4)

        score = round((diversification_score + bankroll_discipline + expected_value + (100 - drawdown) + (100 - risk_score)) / 5, 1)
        return {
            "score": max(0, min(100, score)),
            "strength": "Good bankroll control",
            "weakness": portfolio.get("weakness", "NBA concentration"),
        }
