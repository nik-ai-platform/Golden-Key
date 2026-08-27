class BetSettlementService:
    def settle_bet(self, bet, outcome):
        bet = bet or {}
        outcome = (outcome or "LOSS").upper()
        stake = float(bet.get("stake", 0) or 0)
        odds = float(bet.get("odds", 0) or 0)
        payout = round(stake * odds, 2) if outcome == "WIN" else 0.0
        net = round(payout - stake, 2) if outcome == "WIN" else round(-stake, 2)

        return {
            "status": "SETTLED",
            "result": outcome,
            "payout": payout,
            "net": net,
        }
