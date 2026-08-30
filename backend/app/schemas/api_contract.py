from pydantic import BaseModel, Field


class TodayPredictionItem(BaseModel):
    prediction_id: int
    game_id: int
    sport: str
    home_team: str
    away_team: str
    game_date: str
    market: str
    selection: str
    display_selection: str = ""
    line_value: float | None = None
    american_odds: int | None = None
    model_version: str
    npi_score: float
    confidence_score: float | None = None
    simulation_probability: float | None = None
    projected_edge: float | None = None
    risk_level: str | None = None
    reasoning: str | None = None
    outcome: str | None = None


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
    home_score: float | None = None
    away_score: float | None = None
    predictions: list[TodayPredictionItem]


class SavedPickItem(BaseModel):
    saved_pick_id: int
    prediction_id: int
    game_id: int
    sport: str
    game_date: str
    home_team: str
    away_team: str
    matchup: str
    market: str
    selection: str
    display_selection: str
    line_value: float | None = None
    american_odds: int | None = None
    npi_score: float
    confidence_score: float | None = None
    risk_level: str | None = None
    outcome: str | None = None
    home_score: float | None = None
    away_score: float | None = None


class SavedPicksResponse(BaseModel):
    count: int
    picks: list[SavedPickItem]


class RemoveSavedPredictionResponse(BaseModel):
    removed: bool
    prediction_id: int


class PerformanceBreakdown(BaseModel):
    name: str
    settled: int
    wins: int
    losses: int
    pushes: int
    win_rate: float | None = None


class RecentResultItem(BaseModel):
    prediction_id: int
    game_id: int
    sport: str
    game_date: str
    home_team: str
    away_team: str
    market: str
    display_selection: str
    npi_score: float
    outcome: str
    home_score: float | None = None
    away_score: float | None = None


class PerformanceResponse(BaseModel):
    total_predictions: int
    wins: int
    losses: int
    pushes: int
    accuracy: float
    profit_loss: float
    market_performance: list[PerformanceBreakdown] = Field(default_factory=list)
    sport_performance: list[PerformanceBreakdown] = Field(default_factory=list)
    recent_results: list[RecentResultItem] = Field(default_factory=list)
