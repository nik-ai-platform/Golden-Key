from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.golden_key_engine import GoldenKeyEngine
from app.services.service_registry import ServiceRegistry


class DailyPipelineService:
    def __init__(self, registry: ServiceRegistry | None = None) -> None:
        self.registry = registry or ServiceRegistry()
        self.engine = GoldenKeyEngine(self.registry)

    def run_daily_workflow(self, run_time: str = "06:00") -> dict[str, Any]:
        games = self.registry.game.import_today_games()
        odds = self.registry.odds.import_odds(games)

        picks: list[dict[str, Any]] = []
        for game, game_odds in zip(games, odds):
            prediction = self.engine.generate_prediction(game)
            picks.append(
                {
                    "game": f"{game['home_team']} vs {game['away_team']}",
                    "NPI": prediction["npi_score"],
                    "prediction": prediction["pick"],
                    "confidence": prediction["confidence"],
                    "risk": prediction["risk_score"],
                    "odds": game_odds,
                }
            )

        top_pick = max(picks, key=lambda item: float(item["confidence"])) if picks else None

        return {
            "scheduled_time": run_time,
            "executed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "stages": [
                "Import Games",
                "Import Odds",
                "Calculate NPI",
                "Run Models",
                "Run Simulation",
                "AI Analysis",
                "Generate Picks",
                "Publish Dashboard",
            ],
            "picks": picks,
            "top_pick": top_pick,
            "published": True,
        }
