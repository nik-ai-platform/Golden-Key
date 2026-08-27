from __future__ import annotations

from typing import Any


class GameMonteCarloService:
    def run(self, game: dict[str, Any], simulations: int) -> dict[str, Any]:
        home_team = str(game.get("home_team", "Home"))
        away_team = str(game.get("away_team", "Away"))
        return {
            "simulations": simulations,
            "score_distribution": {
                f"{home_team} 24-30": 38,
                f"{home_team} 31+": 21,
                f"{away_team} win": 36,
            },
        }
