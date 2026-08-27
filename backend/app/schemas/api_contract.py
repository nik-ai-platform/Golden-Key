from pydantic import BaseModel


class TodayPredictionItem(BaseModel):
    prediction_id: int
    game_id: int
    sport: str
    home_team: str
    away_team: str
    game_date: str
    market: str
    selection: str
    model_version: str
    npi_score: float
    confidence_score: float | None = None
    simulation_probability: float | None = None
    projected_edge: float | None = None
    risk_level: str | None = None
    reasoning: str | None = None


class TodayPredictionsResponse(BaseModel):
    sport: str | None = None
    count: int
    predictions: list[TodayPredictionItem]


class GameDetailResponse(BaseModel):
    game_id: int
    sport: str
    home_team: str
    away_team: str
    game_date: str
    prediction: TodayPredictionItem | None = None


class SavedPickItem(BaseModel):
    saved_pick_id: int
    prediction_id: int
    game_id: int
    market: str
    selection: str
    confidence_score: float | None = None
    outcome: str | None = None


class SavedPicksResponse(BaseModel):
    count: int
    picks: list[SavedPickItem]


class PerformanceResponse(BaseModel):
    total_predictions: int
    wins: int
    losses: int
    pushes: int
    accuracy: float
    profit_loss: float
