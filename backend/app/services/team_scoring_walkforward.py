from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Iterable


@dataclass(frozen=True)
class GamePeriod:
    game_id: int
    kickoff: datetime


def split_games_chronologically(
    games: Iterable[GamePeriod],
    *,
    training_fraction: float = 0.6,
    tuning_fraction: float = 0.2,
) -> dict[str, tuple[int, ...]]:
    if not 0 < training_fraction < 1 or not 0 < tuning_fraction < 1:
        raise ValueError("training_fraction and tuning_fraction must be between 0 and 1")
    if training_fraction + tuning_fraction >= 1:
        raise ValueError("training and tuning fractions must leave a final test period")

    ordered: dict[int, datetime] = {}
    for game in games:
        current = ordered.get(game.game_id)
        if current is None or _timestamp(game.kickoff) < _timestamp(current):
            ordered[game.game_id] = game.kickoff
    timeline = tuple(
        sorted(
            ordered.items(),
            key=lambda item: (_timestamp(item[1]), item[0]),
        )
    )
    count = len(timeline)
    train_end = min(count, max(1, int(count * training_fraction))) if count else 0
    tuning_count = ceil(count * tuning_fraction) if count > 1 else 0
    tuning_end = min(count - 1, train_end + tuning_count) if count > 1 else count
    return {
        "training": tuple(game_id for game_id, _ in timeline[:train_end]),
        "tuning": tuple(game_id for game_id, _ in timeline[train_end:tuning_end]),
        "final_test": tuple(game_id for game_id, _ in timeline[tuning_end:]),
    }


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).timestamp()
