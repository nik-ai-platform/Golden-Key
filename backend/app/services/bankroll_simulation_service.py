class BankrollSimulationService:

    def simulate(self, starting_bankroll, results):
        bankroll = float(starting_bankroll or 0)
        wins = 0
        losses = 0
        max_drawdown = 0.0
        for item in results or []:
            if item.get("win"):
                bankroll += float(item.get("payout") or 0)
                wins += 1
            else:
                bankroll -= float(item.get("bet_size") or 0)
                losses += 1
            max_drawdown = max(max_drawdown, (starting_bankroll - bankroll) / starting_bankroll * 100 if starting_bankroll else 0.0)

        roi = ((bankroll - starting_bankroll) / starting_bankroll * 100) if starting_bankroll else 0.0
        return {
            "starting_bankroll": starting_bankroll,
            "ending_bankroll": round(bankroll, 2),
            "wins": wins,
            "losses": losses,
            "profit": round(bankroll - starting_bankroll, 2),
            "loss_streaks": losses,
            "maximum_drawdown": round(max_drawdown, 2),
            "roi": round(roi, 2),
        }
