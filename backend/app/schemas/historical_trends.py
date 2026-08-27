from pydantic import BaseModel


class TrendPoint(BaseModel):

    period: str

    accuracy: float

    confidence: float

    predictions: int

    correct: int | None = None


class HistoricalTrendResponse(BaseModel):

    daily: list[TrendPoint]

    weekly: list[TrendPoint]

    monthly: list[TrendPoint]


class TeamTrendWindow(BaseModel):

    accuracy: float

    momentum: float


class TeamTrendResponse(BaseModel):

    team: str

    last30: TeamTrendWindow


class SportTrendPoint(BaseModel):

    sport: str

    accuracy: float


class ModelTrendPoint(BaseModel):

    version: str

    accuracy: float