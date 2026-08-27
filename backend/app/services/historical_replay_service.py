class HistoricalReplayService:

    def replay(self, strategy, historical_games):
        if not historical_games:
            return {"strategy": strategy.get("sport"), "games_replayed": 0, "status": "no_data"}

        return {
            "strategy": strategy.get("sport"),
            "games_replayed": len(historical_games),
            "status": "replayed",
        }
