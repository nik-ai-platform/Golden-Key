class MarketDataService:
    def ingest_odds(self, odds_data):
        odds_data = odds_data or {}
        return {
            "game_id": odds_data.get("game_id", 1),
            "sportsbook": odds_data.get("sportsbook", "DraftKings"),
            "market_type": odds_data.get("market_type", "spread"),
            "spread": odds_data.get("spread", "KC -3"),
            "moneyline": odds_data.get("moneyline", "-110"),
            "total": odds_data.get("total", "48.5"),
            "timestamp": odds_data.get("timestamp"),
        }

    def update_market(self, game_id):
        return {
            "game_id": game_id,
            "status": "updated",
            "snapshot": [{"sportsbook": "DraftKings", "spread": "KC -3", "moneyline": "-110"}],
        }

    def get_market_snapshot(self, game_id):
        return {
            "game_id": game_id,
            "markets": [
                {"sportsbook": "DraftKings", "market_type": "spread", "spread": "KC -3", "moneyline": "-110"},
                {"sportsbook": "FanDuel", "market_type": "spread", "spread": "KC -3.5", "moneyline": "-105"},
            ],
        }
