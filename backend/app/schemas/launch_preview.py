from datetime import datetime

from pydantic import BaseModel


class SlatePreviewGame(BaseModel):
    game_id: int
    sport: str
    league: str
    home_team: str
    away_team: str
    start_time: datetime
    status: str


class SlatePreviewResponse(BaseModel):
    sport: str | None
    count: int
    games: list[SlatePreviewGame]
