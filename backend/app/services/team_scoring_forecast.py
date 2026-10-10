from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

import numpy as np

MODEL_VERSION = "TEAM-SCORING-RIDGE-1.0"
ACTIVATION_ENABLED = False
RIDGE_PENALTY = 20.0
MIN_TEAM_GAMES = 3
MIN_TRAINING_GAMES = 8
MIN_CALIBRATION_ERRORS = 30
PUSH_TOLERANCE = 1e-9


@dataclass(frozen=True)
class TimestampedScore:
    game_id: int
    sport: str
    home_team_id: int
    away_team_id: int
    kickoff: datetime
    observed_at: datetime
    neutral_site: bool | None
    home_score: float | None
    away_score: float | None
    status: str
    observation_id: int
    source_provider: str | None = None
    source_game_id: str | None = None
    source_updated_at: datetime | None = None
    receipt_basis: str | None = None


@dataclass(frozen=True)
class TeamScoringForecast:
    home_margin: float
    training_games: int
    home_team_games: int
    away_team_games: int
    ridge_penalty: float
    model_version: str = MODEL_VERSION


@dataclass(frozen=True)
class TeamScoringRatings:
    team_ids: tuple[int, ...]
    offense: tuple[float, ...]
    defense_allowed: tuple[float, ...]
    appearances: tuple[int, ...]
    home_advantage: float
    training_games: int
    ridge_penalty: float

    def predict_home_margin(
        self,
        home_team_id: int,
        away_team_id: int,
        neutral_site: bool,
    ) -> float:
        home_index = self.team_ids.index(home_team_id)
        away_index = self.team_ids.index(away_team_id)
        return (
            self.offense[home_index]
            - self.offense[away_index]
            + self.defense_allowed[away_index]
            - self.defense_allowed[home_index]
            + (0.0 if neutral_site else self.home_advantage)
        )


@dataclass(frozen=True)
class CoverProbabilities:
    home_cover: float
    away_cover: float
    push: float
    calibration_games: int


def available_scores_as_of(
    observations: Iterable[TimestampedScore],
    *,
    sport: str,
    as_of: datetime,
    exclude_game_id: int,
) -> tuple[TimestampedScore, ...]:
    cutoff = _timestamp(as_of)
    latest: dict[int, TimestampedScore] = {}
    for item in observations:
        if item.game_id == exclude_game_id or item.sport.upper() != sport.upper():
            continue
        if _timestamp(item.kickoff) >= cutoff or _timestamp(item.observed_at) >= cutoff:
            continue
        previous = latest.get(item.game_id)
        if previous is None or (
            _timestamp(item.observed_at),
            item.observation_id,
        ) > (
            _timestamp(previous.observed_at),
            previous.observation_id,
        ):
            latest[item.game_id] = item

    return tuple(
        sorted(
            (
                item
                for item in latest.values()
                if item.status.strip().lower() in {"final", "completed"}
                and _valid_score(item.home_score)
                and _valid_score(item.away_score)
                and item.neutral_site is not None
                and item.home_team_id != item.away_team_id
            ),
            key=lambda item: (item.kickoff, item.game_id),
        )
    )


def forecast_home_margin(
    observations: Iterable[TimestampedScore],
    *,
    sport: str,
    home_team_id: int,
    away_team_id: int,
    neutral_site: bool | None,
    as_of: datetime,
    target_game_id: int,
    ridge_penalty: float = RIDGE_PENALTY,
    min_team_games: int = MIN_TEAM_GAMES,
    min_training_games: int = MIN_TRAINING_GAMES,
) -> TeamScoringForecast | None:
    if home_team_id == away_team_id:
        raise ValueError("home_team_id and away_team_id must differ")
    if neutral_site is None:
        return None
    if not math.isfinite(ridge_penalty) or ridge_penalty <= 0:
        raise ValueError("ridge_penalty must be finite and positive")
    if min_team_games < 1 or min_training_games < 1:
        raise ValueError("minimum history requirements must be positive")

    history = available_scores_as_of(
        observations,
        sport=sport,
        as_of=as_of,
        exclude_game_id=target_game_id,
    )
    appearances: dict[int, int] = {}
    for game in history:
        appearances[game.home_team_id] = appearances.get(game.home_team_id, 0) + 1
        appearances[game.away_team_id] = appearances.get(game.away_team_id, 0) + 1
    home_games = appearances.get(home_team_id, 0)
    away_games = appearances.get(away_team_id, 0)
    if (
        len(history) < min_training_games
        or home_games < min_team_games
        or away_games < min_team_games
    ):
        return None

    ratings = _fit_team_scoring_ratings(history, ridge_penalty)
    if ratings is None:
        return None
    return TeamScoringForecast(
        home_margin=ratings.predict_home_margin(
            home_team_id,
            away_team_id,
            neutral_site,
        ),
        training_games=ratings.training_games,
        home_team_games=home_games,
        away_team_games=away_games,
        ridge_penalty=ridge_penalty,
    )


@lru_cache(maxsize=256)
def _fit_team_scoring_ratings(
    history: tuple[TimestampedScore, ...],
    ridge_penalty: float,
) -> TeamScoringRatings | None:
    if len(history) < MIN_TRAINING_GAMES:
        return None
    appearances: dict[int, int] = {}
    for game in history:
        appearances[game.home_team_id] = appearances.get(game.home_team_id, 0) + 1
        appearances[game.away_team_id] = appearances.get(game.away_team_id, 0) + 1
    team_ids = sorted(appearances)
    team_column = {team_id: index for index, team_id in enumerate(team_ids)}
    baseline_column = 0
    home_advantage_column = 1
    offense_start = 2
    defense_start = offense_start + len(team_ids)
    parameter_count = defense_start + len(team_ids)
    design = np.zeros((len(history) * 2, parameter_count), dtype=np.float64)
    outcomes = np.zeros(len(history) * 2, dtype=np.float64)

    for index, game in enumerate(history):
        home_row = index * 2
        away_row = home_row + 1
        home_col = team_column[game.home_team_id]
        away_col = team_column[game.away_team_id]

        design[home_row, baseline_column] = 1.0
        design[home_row, home_advantage_column] = 0.0 if game.neutral_site else 1.0
        design[home_row, offense_start + home_col] = 1.0
        design[home_row, defense_start + away_col] = 1.0
        outcomes[home_row] = float(game.home_score)

        design[away_row, baseline_column] = 1.0
        design[away_row, offense_start + away_col] = 1.0
        design[away_row, defense_start + home_col] = 1.0
        outcomes[away_row] = float(game.away_score)

    penalty = np.eye(parameter_count, dtype=np.float64) * ridge_penalty
    penalty[baseline_column, baseline_column] = 0.0
    coefficients = np.linalg.solve(
        design.T @ design + penalty,
        design.T @ outcomes,
    )
    return TeamScoringRatings(
        team_ids=tuple(team_ids),
        offense=tuple(
            float(coefficients[offense_start + index]) for index in range(len(team_ids))
        ),
        defense_allowed=tuple(
            float(coefficients[defense_start + index]) for index in range(len(team_ids))
        ),
        appearances=tuple(appearances[team_id] for team_id in team_ids),
        home_advantage=float(coefficients[home_advantage_column]),
        training_games=len(history),
        ridge_penalty=ridge_penalty,
    )


def estimate_cover_probabilities(
    *,
    forecast_home_margin: float,
    spread_home: float,
    earlier_forecast_errors: Iterable[float],
    minimum_errors: int = MIN_CALIBRATION_ERRORS,
) -> CoverProbabilities | None:
    if not math.isfinite(forecast_home_margin) or not math.isfinite(spread_home):
        raise ValueError("forecast_home_margin and spread_home must be finite")
    errors = tuple(float(value) for value in earlier_forecast_errors)
    if any(not math.isfinite(value) for value in errors):
        raise ValueError("forecast errors must be finite")
    if minimum_errors < 1:
        raise ValueError("minimum_errors must be positive")
    if len(errors) < minimum_errors:
        return None

    home_wins = home_losses = pushes = 0
    for error in errors:
        covered_margin = forecast_home_margin + error + spread_home
        if abs(covered_margin) <= PUSH_TOLERANCE:
            pushes += 1
        elif covered_margin > 0:
            home_wins += 1
        else:
            home_losses += 1

    denominator = len(errors)
    return CoverProbabilities(
        home_cover=home_wins / denominator,
        away_cover=home_losses / denominator,
        push=pushes / denominator,
        calibration_games=denominator,
    )


def _valid_score(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) >= 0


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).timestamp()
