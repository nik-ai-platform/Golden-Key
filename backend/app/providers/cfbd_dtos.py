from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CFBDTeam:
    id: int
    school: str
    alternate_names: tuple[str, ...] = ()
    abbreviation: str | None = None
    metadata_complete: bool = True


@dataclass(frozen=True)
class CFBDTeamSeason:
    team_id: int
    school: str
    conference: str | None
    classification: str | None
    division: str | None
    is_fbs: bool | None


@dataclass(frozen=True)
class CFBDGame:
    id: int
    season: int
    start_date: datetime
    home_id: int
    away_id: int
    home_team: str
    away_team: str
    home_points: float | None
    away_points: float | None
    completed: bool
    neutral_site: bool | None
    venue_name: str | None
    venue_city: str | None
    venue_state: str | None
    source_updated_at: datetime | None = None