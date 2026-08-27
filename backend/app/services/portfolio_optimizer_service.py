from __future__ import annotations


class PortfolioOptimizerService:
    def optimize(self, allocation: dict | None) -> dict:
        allocation = allocation or {}
        nba = float(allocation.get("NBA", 0) or 0)
        nfl = float(allocation.get("NFL", 0) or 0)
        ncaab = float(allocation.get("NCAAB", 0) or 0)
        total = nba + nfl + ncaab or 1.0
        nba_pct = round((nba / total) * 100, 1)
        nfl_pct = round((nfl / total) * 100, 1)
        ncaab_pct = round((ncaab / total) * 100, 1)
        recommendation = "Increase diversification." if nba_pct > 50 else "Maintain balance."
        return {
            "current_allocation": {"NBA": nba_pct, "NFL": nfl_pct, "NCAAB": ncaab_pct},
            "recommendation": recommendation,
            "action": "Reduce NBA exposure." if nba_pct > 50 else "Optimize current mix.",
        }
