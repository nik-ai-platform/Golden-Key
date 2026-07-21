from datetime import datetime

from pydantic import BaseModel


class GameBase(BaseModel):
    sport: str
    league: str
    season: int | None = None
    home_team_id: int
    away_team_id: int
    game_date: datetime
    status: str


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    sport: str | None = None
    league: str | None = None
    season: int | None = None
    home_team_id: int | None = None
    away_team_id: int | None = None
    game_date: datetime | None = None
    status: str | None = None


class GameResponse(GameBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
