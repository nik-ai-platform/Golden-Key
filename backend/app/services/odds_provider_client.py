from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings


class OddsProviderClient:

    def __init__(self) -> None:
        self.base_url = settings.ODDS_API_BASE_URL.rstrip("/")
        self.api_key = settings.ODDS_API_KEY

    def get_odds(
        self,
        sport_key: str,
        regions: str = "us",
        markets: str = "h2h,spreads,totals",
        odds_format: str = "american",
    ) -> list[dict[str, Any]]:

        if not self.api_key or self.api_key == "your_actual_key":
            raise ValueError("ODDS_API_KEY is not configured")

        url = f"{self.base_url}/sports/{sport_key}/odds"
        response = requests.get(
            url,
            params={
                "apiKey": self.api_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
            },
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected odds provider response")

        return payload

    def get_scores(
        self,
        sport_key: str,
        *,
        days_from: int = 3,
    ) -> list[dict[str, Any]]:
        if not self.api_key or self.api_key == "your_actual_key":
            raise ValueError("ODDS_API_KEY is not configured")

        url = f"{self.base_url}/sports/{sport_key}/scores/"
        response = requests.get(
            url,
            params={
                "daysFrom": days_from,
                "apiKey": self.api_key,
            },
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Odds API scores response must be a list")

        return payload
