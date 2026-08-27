from typing import Any

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    system_health: str
    overall_accuracy: float
    total_predictions: int
    recent_predictions: list[Any]
    top_teams: list[Any]
    model_versions: list[Any]
    model_lab: Any | None = None
