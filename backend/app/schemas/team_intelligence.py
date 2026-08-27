from pydantic import BaseModel


class TeamIntelligence(BaseModel):

    team_id: int

    team_name: str

    momentum: float

    consistency: float

    trend: str

    home_win_pct: float

    away_win_pct: float

    average_margin: float

    offensive_rating: float

    defensive_rating: float

    strength_rating: float


class TeamIntelligenceSummary(BaseModel):
    team: str | None = None
    record: str
    last10: str
    offense: float
    defense: float
    momentum: float
    strength: float