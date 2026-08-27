from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GameBase(BaseModel):
    sport: str
    league: str
    season: int

    game_date: datetime

    home_team_id: int
    away_team_id: int


class GameCreate(GameBase):
    pass


class GameUpdate(BaseModel):
    sport: str | None = None
    league: str | None = None
    season: int | None = None

    game_date: datetime | None = None

    home_team_id: int | None = None
    away_team_id: int | None = None


class GameResponse(GameBase):
    id: int
    home_score: float | None = None
    away_score: float | None = None
    winner_team_id: int | None = None
    model_config = ConfigDict(from_attributes=True)
