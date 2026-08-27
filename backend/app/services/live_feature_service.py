class LiveFeatureService:

    def build_features(self, game_state):
        if not game_state:
            return {
                "current_pace": 0,
                "shooting_efficiency": 0,
                "turnover_rate": 0,
                "foul_trouble": 0,
                "run_differential": 0,
                "momentum": 0,
            }

        return {
            "current_pace": game_state.get("current_pace", 100),
            "shooting_efficiency": game_state.get("shooting_efficiency", 0.45),
            "turnover_rate": game_state.get("turnover_rate", 0.12),
            "foul_trouble": game_state.get("foul_trouble", 2),
            "run_differential": game_state.get("run_differential", 0),
            "momentum": game_state.get("momentum_score", 0),
        }
