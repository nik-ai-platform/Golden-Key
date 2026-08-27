from __future__ import annotations

from typing import Any


class FeaturePipelineService:
    FEATURE_VERSION = "features-v1"

    def generate(self, games: list[dict[str, Any]], odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        odds_by_game = {item.get("game_id"): item for item in odds}
        output: list[dict[str, Any]] = []
        for game in games:
            game_id = game.get("id")
            game_odds = odds_by_game.get(game_id, {})
            output.append(
                {
                    "game_id": game_id,
                    "version": self.FEATURE_VERSION,
                    "rest": 2,
                    "travel": 1,
                    "injuries": 0,
                    "momentum": 0.58,
                    "home_away": "home",
                    "weather": "neutral",
                    "market_movement": float(game_odds.get("spread", 0)) * -0.1,
                    "schedule_compression": 0.3,
                }
            )
        return output
