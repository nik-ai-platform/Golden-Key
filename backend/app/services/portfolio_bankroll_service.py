class PortfolioBankrollService:
    def summarize(self, portfolio):
        portfolio = portfolio or {}
        starting = float(portfolio.get("starting_bankroll", 0) or 0)
        current = float(portfolio.get("current_bankroll", starting) or starting)
        profit_loss = round(current - starting, 2)
        roi = round(((current - starting) / starting) * 100, 2) if starting else 0.0
        drawdown = round(max(0.0, ((starting - current) / starting) * 100), 2) if starting else 0.0
        available = round(current - float(portfolio.get("total_exposure", 0) or 0), 2)

        return {
            "starting_bankroll": starting,
            "current_bankroll": current,
            "units": round(current / 1000, 2),
            "profit_loss": profit_loss,
            "roi": roi,
            "drawdown": drawdown,
            "available_capital": available,
        }
