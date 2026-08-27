from __future__ import annotations

from typing import Any


class OddsNormalizerService:

    def normalize_game(
        self,
        payload: dict[str, Any],
        sport: str,
    ) -> dict[str, Any]:

        return {
            "external_id": payload["id"],
            "sport": sport.upper(),
            "home_team": payload["home_team"],
            "away_team": payload["away_team"],
            "commence_time": payload["commence_time"],
        }

    def normalize_bookmaker(
        self,
        game_payload: dict[str, Any],
        bookmaker: dict[str, Any],
    ) -> dict[str, Any]:

        home_team = game_payload["home_team"]
        away_team = game_payload["away_team"]
        spread_home = None
        spread_away = None
        moneyline_home = None
        moneyline_away = None
        total = None

        for market in bookmaker.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            if key == "spreads":
                for outcome in outcomes:
                    if outcome.get("name") == home_team:
                        spread_home = outcome.get("point")
                    elif outcome.get("name") == away_team:
                        spread_away = outcome.get("point")

            elif key == "h2h":
                for outcome in outcomes:
                    if outcome.get("name") == home_team:
                        moneyline_home = outcome.get("price")
                    elif outcome.get("name") == away_team:
                        moneyline_away = outcome.get("price")

            elif key == "totals":
                for outcome in outcomes:
                    if outcome.get("name") == "Over":
                        total = outcome.get("point")
                        break

        return {
            "sportsbook": bookmaker.get(
                "title",
                bookmaker.get("key", "unknown"),
            ),
            "spread_home": spread_home,
            "spread_away": spread_away,
            "moneyline_home": moneyline_home,
            "moneyline_away": moneyline_away,
            "total": total,
        }
