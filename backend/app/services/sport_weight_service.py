class SportWeightService:
    def get_weights(self, sport):
        weights = {
            "NBA": {"pace": 25, "efficiency": 20, "rest": 15},
            "NFL": {"matchup": 15, "weather": 10, "injury": 20},
            "NCAAB": {"tempo": 22, "shot_profile": 18, "rest": 14},
        }
        return {"sport": (sport or "NBA").upper(), "weights": weights.get((sport or "NBA").upper(), {"pace": 10})}
