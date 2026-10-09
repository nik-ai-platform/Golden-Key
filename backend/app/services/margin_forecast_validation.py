from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Callable, Iterable


@dataclass(frozen=True)
class MarginForecastObservation:
    game_id: int
    kickoff: datetime
    published_at: datetime
    sport: str
    model_version: str
    actual_home_margin: float
    market_implied_home_margin: float
    incumbent_home_margin: float | None


def chronological_holdout(
    observations: Iterable[MarginForecastObservation],
    holdout_fraction: float = 0.2,
) -> tuple[tuple[MarginForecastObservation, ...], tuple[MarginForecastObservation, ...]]:
    if not math.isfinite(holdout_fraction) or not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between 0 and 1")

    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (_utc_timestamp(item.kickoff), item.game_id),
        )
    )
    if len(ordered) < 2:
        return ordered, ()

    holdout_count = min(
        len(ordered) - 1,
        max(1, ceil(len(ordered) * holdout_fraction)),
    )
    split_at = len(ordered) - holdout_count
    return ordered[:split_at], ordered[split_at:]


def evaluate_chronological_holdout(
    observations: Iterable[MarginForecastObservation],
    holdout_fraction: float = 0.2,
) -> dict:
    history, heldout = chronological_holdout(observations, holdout_fraction)
    incumbent_records = tuple(
        item for item in heldout if item.incumbent_home_margin is not None
    )
    return {
        "history_prefix_games": len(history),
        "heldout_games": len(heldout),
        "market_candidate": margin_error_metrics(
            heldout,
            lambda item: item.market_implied_home_margin,
        ),
        "incumbent_npi_margin": margin_error_metrics(
            incumbent_records,
            lambda item: item.incumbent_home_margin,
        ),
    }


def margin_error_metrics(
    observations: Iterable[MarginForecastObservation],
    forecast: Callable[[MarginForecastObservation], float | None],
) -> dict:
    errors = [
        value - item.actual_home_margin
        for item in observations
        if (value := forecast(item)) is not None
    ]
    if not errors:
        return {
            "sample_size": 0,
            "mae": None,
            "rmse": None,
            "mean_error": None,
        }

    return {
        "sample_size": len(errors),
        "mae": round(sum(abs(error) for error in errors) / len(errors), 4),
        "rmse": round(math.sqrt(sum(error * error for error in errors) / len(errors)), 4),
        "mean_error": round(sum(errors) / len(errors), 4),
    }


def _utc_timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).timestamp()
