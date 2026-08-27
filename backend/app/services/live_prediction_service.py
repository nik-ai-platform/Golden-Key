class LivePredictionService:

    def predict_live_outcome(self, live_features):
        if not live_features:
            return {
                "team": "Unknown",
                "win_probability": 0,
                "confidence": 0,
                "momentum": "neutral",
            }

        momentum = float(live_features.get("momentum", 0) or 0)
        confidence = max(0, min(100, 50 + int(momentum)))
        win_probability = max(0, min(100, 50 + int(momentum / 2)))
        return {
            "team": live_features.get("team", "Unknown"),
            "win_probability": win_probability,
            "confidence": confidence,
            "momentum": "positive" if momentum > 0 else "negative" if momentum < 0 else "neutral",
        }

    def update_probability(self, game_state):
        if not game_state:
            return {
                "win_probability": 0,
                "confidence": 0,
            }

        momentum = float(game_state.get("momentum_score", 0) or 0)
        return {
            "win_probability": max(0, min(100, 50 + int(momentum))),
            "confidence": max(0, min(100, 60 + int(abs(momentum)))),
        }
