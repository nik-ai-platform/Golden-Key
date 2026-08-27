class BetManagementService:
    def create_bet(self, bet):
        bet = bet or {}
        return {
            "id": bet.get("id", 1),
            "portfolio_id": bet.get("portfolio_id", 1),
            "sport": bet.get("sport", "NBA"),
            "market": bet.get("market", "ATS"),
            "selection": bet.get("selection", "Boston -3.5"),
            "stake": bet.get("stake", 100),
            "confidence": bet.get("confidence", 82),
            "status": bet.get("status", "OPEN"),
            "result": bet.get("result"),
        }

    def update_bet_result(self, bet_id):
        return {
            "id": bet_id,
            "status": "SETTLED",
            "result": "WIN",
        }

    def get_active_bets(self, user_id):
        return [
            {
                "id": 1,
                "portfolio_id": 1,
                "user_id": user_id,
                "sport": "NBA",
                "market": "ATS",
                "selection": "Boston -3.5",
                "stake": 100,
                "confidence": 82,
                "status": "OPEN",
            }
        ]

    def calculate_exposure(self, portfolio):
        if not portfolio:
            return 0.0

        total_stake = float(portfolio.get("total_stake", 0) or 0)
        bankroll = float(portfolio.get("current_bankroll", 0) or 0)
        if bankroll <= 0:
            return 0.0
        return round((total_stake / bankroll) * 100, 2)
