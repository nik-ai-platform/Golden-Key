from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime


class DataValidationService:
    def validate(self, games: list[dict], odds: list[dict]) -> dict:
        errors: list[str] = []
        warnings: list[str] = []

        if not games:
            errors.append("No games found")
        if not odds:
            errors.append("Missing odds")

        team_missing = [game for game in games if not game.get("home_team") or not game.get("away_team")]
        if team_missing:
            errors.append("Missing teams")

        duplicate_ids = [game_id for game_id, count in Counter([game.get("id") for game in games]).items() if count > 1]
        if duplicate_ids:
            errors.append(f"Duplicate games: {duplicate_ids}")

        spreads = [item.get("spread") for item in odds if "spread" in item]
        invalid_spreads = [spread for spread in spreads if not isinstance(spread, (int, float))]
        if invalid_spreads:
            errors.append("Invalid spreads")

        game_times = [game.get("game_time") for game in games if game.get("game_time")]
        if len(game_times) != len(set(game_times)):
            warnings.append("Time conflicts")

        injuries_missing = [game for game in games if game.get("injuries") is None]
        if injuries_missing:
            warnings.append("Missing injuries")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
