from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionBase(BaseModel):
    game_id: int
    market: str
    selection: str


class PredictionFields(PredictionBase):
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


class PredictionCreate(PredictionFields):
    model_config = ConfigDict(allow_inf_nan=False)
    win_probability: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    simulation_probability: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)


class PredictionShadowCreate(PredictionCreate):
    upset_signal: float | None = None


class HistoricalPredictionFields(PredictionFields):
    npi_score: float | None = None
    model_version: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("win_probability", "simulation_probability", mode="before")
    @classmethod
    def available_historical_probability(cls, value: object) -> float | None:
        # The services package imports creation schemas during initialization.
        from app.services.prediction_metric_contract import historical_probability

        return historical_probability(value)

    @field_validator(
        "npi_score", "confidence_score", "projected_edge", "line_value",
        "simulation_margin", mode="before",
    )
    @classmethod
    def available_historical_metric(cls, value: object) -> float | None:
        from app.services.prediction_metric_contract import finite_metric

        return finite_metric(value)

    @field_validator("simulation_runs", "odds_snapshot_id", mode="before")
    @classmethod
    def available_historical_integer(cls, value: object) -> int | None:
        from app.services.prediction_metric_contract import historical_integer

        return historical_integer(value)

    @field_validator("risk_level", "sportsbook", "model_version", "reasoning", mode="before")
    @classmethod
    def available_historical_text(cls, value: object) -> str | None:
        from app.services.prediction_metric_contract import historical_text

        return historical_text(value)

    @field_validator("market", "selection", mode="before")
    @classmethod
    def available_historical_selection(cls, value: object) -> str:
        from app.services.prediction_metric_contract import historical_text

        return historical_text(value) or "unavailable"

    @field_validator("american_odds", mode="before")
    @classmethod
    def available_historical_price(cls, value: object) -> int | None:
        from app.services.prediction_metric_contract import historical_price

        return historical_price(value)


class PredictionResponse(HistoricalPredictionFields):
    id: int
    created_at: datetime
