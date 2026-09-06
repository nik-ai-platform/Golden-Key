from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.providers.cfbd_dtos import CFBDGame, CFBDTeam, CFBDTeamSeason


class CFBDClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.CFBD_API_KEY
        self.base_url = (base_url or settings.CFBD_API_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.REQUEST_TIMEOUT_SECONDS
        self._client = client

    def get_teams(self, season: int) -> list[CFBDTeam]:
        payload = self._get("/teams", {"year": season})
        return [self._map_team(item) for item in payload]

    def get_team_metadata(self, season: int) -> list[CFBDTeamSeason]:
        payload = self._get("/teams", {"year": season})
        return [self._map_team_season(item) for item in payload]

    def get_games(self, season: int) -> list[CFBDGame]:
        payload = self._get("/games", {"year": season})
        return [self._map_game(item) for item in payload]

    def _get(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.api_key:
            raise ValueError("CFBD_API_KEY is required")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self._client is not None:
            response = self._client.get(path, params=params, headers=headers)
        else:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                headers=headers,
            ) as client:
                response = client.get(path, params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected CFBD response for {path}")
        return data

    @staticmethod
    def _map_team(item: dict[str, Any]) -> CFBDTeam:
        alternate_names = tuple(
            str(name).strip()
            for name in item.get("alternateNames", [])
            if str(name).strip()
        )
        return CFBDTeam(
            id=int(item["id"]),
            school=str(item["school"]).strip(),
            alternate_names=alternate_names,
            abbreviation=_optional_string(item.get("abbreviation")),
        )

    @staticmethod
    def _map_team_season(item: dict[str, Any]) -> CFBDTeamSeason:
        classification = _optional_string(item.get("classification"))
        return CFBDTeamSeason(
            team_id=int(item["id"]),
            school=str(item["school"]).strip(),
            conference=_optional_string(item.get("conference")),
            classification=classification,
            division=_optional_string(item.get("division")),
            is_fbs=_optional_bool(item.get("fbs"), classification),
        )

    @staticmethod
    def _map_game(item: dict[str, Any]) -> CFBDGame:
        raw_venue = item.get("venue")
        venue = raw_venue if isinstance(raw_venue, dict) else {}
        return CFBDGame(
            id=int(item["id"]),
            season=int(item["season"]),
            start_date=_parse_datetime(item["startDate"]),
            home_id=int(item["homeId"]),
            away_id=int(item["awayId"]),
            home_team=str(item["homeTeam"]).strip(),
            away_team=str(item["awayTeam"]).strip(),
            home_points=_optional_float(item.get("homePoints")),
            away_points=_optional_float(item.get("awayPoints")),
            completed=bool(item.get("completed", False)),
            neutral_site=_nullable_bool(item.get("neutralSite")),
            venue_name=_optional_string(venue.get("name") or raw_venue),
            venue_city=_optional_string(venue.get("city")),
            venue_state=_optional_string(venue.get("state")),
            source_updated_at=_optional_datetime(
                item.get("updatedAt") or item.get("lastUpdated")
            ),
        )


def _parse_datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _optional_datetime(value: Any) -> datetime | None:
    return _parse_datetime(value) if value else None


def _optional_string(value: Any) -> str | None:
    if value is None or isinstance(value, dict):
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _nullable_bool(value: Any) -> bool | None:
    return bool(value) if value is not None else None


def _optional_bool(value: Any, classification: str | None) -> bool | None:
    if value is not None:
        return bool(value)
    if classification is None:
        return None
    normalized = classification.upper()
    if normalized == "FBS":
        return True
    if normalized == "FCS":
        return False
    return None