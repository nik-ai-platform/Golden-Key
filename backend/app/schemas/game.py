from datetime import datetime

from pydantic import BaseModel


class GameBase(BaseModel):
    sport: str
    league: str
    season: str

    game_date: datetime

    status: str = "scheduled"

    home_team_id: int
    away_team_id: int


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    sport: str | None = None
    league: str | None = None
    season: str | None = None

    game_date: datetime | None = None

    status: str | None = None

    home_team_id: int | None = None
    away_team_id: int | None = None


class GameResponse(GameBase):
    id: int

    class Config:
        from_attributes = True
