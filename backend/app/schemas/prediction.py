from datetime import datetime

from pydantic import BaseModel


class PredictionBase(BaseModel):
    game_id: int
    market: str
    selection: str


class PredictionCreate(PredictionBase):
    model_version: str
    line_value: float | None = None
    american_odds: int | None = None
    odds_snapshot_id: int | None = None
    sportsbook: str | None = None
    odds_observed_at: datetime | None = None
    npi_score: float
    win_probability: float | None = None
    simulation_probability: float | None = None
    simulation_runs: int | None = None
    simulation_margin: float | None = None
    confidence_score: float | None = None
    projected_edge: float | None = None
    risk_level: str | None = None
    reasoning: str | None = None


class PredictionShadowCreate(PredictionCreate):
    upset_signal: float | None = None


class PredictionResponse(PredictionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
