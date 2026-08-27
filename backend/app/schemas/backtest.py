from datetime import date
from typing import Literal

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    sport: str
    model_version: str
    start_date: date
    end_date: date
    market: Literal["moneyline", "spread", "total"]
