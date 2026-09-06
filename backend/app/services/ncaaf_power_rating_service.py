from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.game_result_observation import GameResultObservation


MODEL_VERSION = "NCAAF-POWER-1.0"
RECENCY_HALF_LIFE_DAYS = 56.0
PROVISIONAL_HOME_FIELD_POINTS = 2.5
MOV_LINEAR_THRESHOLD = 21.0
MOV_LOG_SCALE = 7.0
PRIOR_REGRESSION = 0.50
PRIOR_PSEUDO_GAMES = 4.0


@dataclass(frozen=True)
class TeamPowerRating:
    team_id: int
    rating: float
    uncertainty: float
    games_used: int
    effective_games: float
    as_of_timestamp: datetime
    model_version: str = MODEL_VERSION


@dataclass(frozen=True)
class EligibleGame:
    game_id: int
    home_team_id: int
    away_team_id: int
    game_date: datetime
    home_score: float
    away_score: float
    neutral_site: bool
    observation_id: int
    observation_provider: str
    observation_observed_at: datetime
    observation_source_updated_at: datetime | None
    observation_payload_hash: str | None


@dataclass(frozen=True)
class RatingCalculation:
    ratings: dict[int, TeamPowerRating]
    eligible_games: tuple[EligibleGame, ...]
    residual_rmse: float


def transform_margin(margin: float) -> float:
    magnitude = abs(float(margin))
    if magnitude <= MOV_LINEAR_THRESHOLD:
        return float(margin)
    transformed = MOV_LINEAR_THRESHOLD + MOV_LOG_SCALE * math.log1p(
        (magnitude - MOV_LINEAR_THRESHOLD) / MOV_LOG_SCALE
    )
    return math.copysign(transformed, margin)


def recency_weight(
    game_date: datetime,
    as_of_timestamp: datetime,
    half_life_days: float = RECENCY_HALF_LIFE_DAYS,
) -> float:
    game_date = _require_aware(game_date, "game_date")
    as_of_timestamp = _require_aware(as_of_timestamp, "as_of_timestamp")
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    if game_date > as_of_timestamp:
        raise ValueError("game_date must not be later than as_of_timestamp")
    days_old = (as_of_timestamp - game_date).total_seconds() / 86400.0
    return 2.0 ** (-days_old / half_life_days)


def get_eligible_games(
    db: Session,
    as_of_timestamp: datetime,
    season: int | None = None,
) -> tuple[EligibleGame, ...]:
    as_of_timestamp = _require_aware(as_of_timestamp, "as_of_timestamp")
    database_cutoff = as_of_timestamp.astimezone(UTC).replace(tzinfo=None)
    available_observations = (
        db.query(
            GameResultObservation.id.label("observation_id"),
            GameResultObservation.game_id.label("game_id"),
            GameResultObservation.provider.label("provider"),
            GameResultObservation.home_score.label("home_score"),
            GameResultObservation.away_score.label("away_score"),
            GameResultObservation.observed_at.label("observed_at"),
            GameResultObservation.source_updated_at.label("source_updated_at"),
            GameResultObservation.payload_hash.label("payload_hash"),
            func.row_number()
            .over(
                partition_by=GameResultObservation.game_id,
                order_by=(
                    GameResultObservation.observed_at.desc(),
                    GameResultObservation.id.desc(),
                ),
            )
            .label("observation_rank"),
        )
        .filter(
            GameResultObservation.status == "final",
            GameResultObservation.home_score.isnot(None),
            GameResultObservation.away_score.isnot(None),
            GameResultObservation.observed_at <= database_cutoff,
        )
        .subquery()
    )
    query = (
        db.query(
            Game,
            available_observations.c.observation_id,
            available_observations.c.provider,
            available_observations.c.home_score,
            available_observations.c.away_score,
            available_observations.c.observed_at,
            available_observations.c.source_updated_at,
            available_observations.c.payload_hash,
        )
        .join(available_observations, available_observations.c.game_id == Game.id)
        .filter(
            available_observations.c.observation_rank == 1,
            Game.sport == "NCAAF",
            Game.game_date < database_cutoff,
            Game.status == "final",
        )
    )
    if season is not None:
        query = query.filter(Game.season == season)

    games = []
    for (
        game,
        observation_id,
        observation_provider,
        observed_home_score,
        observed_away_score,
        observation_observed_at,
        observation_source_updated_at,
        observation_payload_hash,
    ) in query.order_by(Game.game_date, Game.id):
        if game.neutral_site is None:
            continue
        games.append(
            EligibleGame(
                game_id=game.id,
                home_team_id=game.home_team_id,
                away_team_id=game.away_team_id,
                game_date=_database_timestamp_as_utc(game.game_date),
                home_score=float(observed_home_score),
                away_score=float(observed_away_score),
                neutral_site=game.neutral_site,
                observation_id=observation_id,
                observation_provider=observation_provider,
                observation_observed_at=_database_timestamp_as_utc(
                    observation_observed_at
                ),
                observation_source_updated_at=(
                    _database_timestamp_as_utc(observation_source_updated_at)
                    if observation_source_updated_at is not None
                    else None
                ),
                observation_payload_hash=observation_payload_hash,
            )
        )
    return tuple(games)


def calculate_rating_result(
    db: Session,
    as_of_timestamp: datetime,
    season: int | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> RatingCalculation:
    as_of_timestamp = _require_aware(as_of_timestamp, "as_of_timestamp")
    games = get_eligible_games(db, as_of_timestamp, season)
    if not games:
        return RatingCalculation({}, games, 0.0)

    team_ids = sorted(
        {team_id for game in games for team_id in (game.home_team_id, game.away_team_id)}
    )
    team_indexes = {team_id: index for index, team_id in enumerate(team_ids)}
    game_weights = np.array(
        [recency_weight(game.game_date, as_of_timestamp) for game in games],
        dtype=float,
    )
    design = np.zeros((len(games), len(team_ids)), dtype=float)
    targets = np.zeros(len(games), dtype=float)
    games_used = {team_id: 0 for team_id in team_ids}
    effective_games = {team_id: 0.0 for team_id in team_ids}

    for row, (game, weight) in enumerate(zip(games, game_weights, strict=True)):
        design[row, team_indexes[game.home_team_id]] = 1.0
        design[row, team_indexes[game.away_team_id]] = -1.0
        home_field = 0.0 if game.neutral_site else PROVISIONAL_HOME_FIELD_POINTS
        targets[row] = transform_margin(game.home_score - game.away_score) - home_field
        for team_id in (game.home_team_id, game.away_team_id):
            games_used[team_id] += 1
            effective_games[team_id] += float(weight)

    sqrt_weights = np.sqrt(game_weights)
    weighted_design = design * sqrt_weights[:, None]
    weighted_targets = targets * sqrt_weights
    prior_rows = np.eye(len(team_ids), dtype=float) * math.sqrt(PRIOR_PSEUDO_GAMES)
    prior_targets = np.array(
        [PRIOR_REGRESSION * (prior_ratings or {}).get(team_id, 0.0) for team_id in team_ids],
        dtype=float,
    ) * math.sqrt(PRIOR_PSEUDO_GAMES)
    matrix = np.vstack((weighted_design, prior_rows))
    values = np.concatenate((weighted_targets, prior_targets))
    raw_ratings = np.linalg.lstsq(matrix, values, rcond=None)[0]

    # Effective-game weighting defines the national reference while the neutral
    # regularization anchors make disconnected schedules independently solvable.
    centering_weights = np.array(
        [effective_games[team_id] + PRIOR_PSEUDO_GAMES for team_id in team_ids],
        dtype=float,
    )
    raw_ratings -= float(np.average(raw_ratings, weights=centering_weights))
    residuals = targets - design @ raw_ratings
    residual_rmse = math.sqrt(float(np.average(residuals**2, weights=game_weights)))

    ratings = {}
    for team_id, rating in zip(team_ids, raw_ratings, strict=True):
        uncertainty_games = effective_games[team_id]
        if prior_ratings is not None and team_id in prior_ratings:
            uncertainty_games += PRIOR_PSEUDO_GAMES
        ratings[team_id] = TeamPowerRating(
            team_id=team_id,
            rating=float(rating),
            # This is a model uncertainty proxy, not a calibrated interval.
            uncertainty=residual_rmse / math.sqrt(max(uncertainty_games, 1.0)),
            games_used=games_used[team_id],
            effective_games=effective_games[team_id],
            as_of_timestamp=as_of_timestamp,
        )
    return RatingCalculation(ratings, games, residual_rmse)


def calculate_team_ratings(
    db: Session,
    as_of_timestamp: datetime,
    season: int | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> dict[int, TeamPowerRating]:
    return calculate_rating_result(db, as_of_timestamp, season, prior_ratings).ratings


def get_team_rating(
    db: Session,
    team_id: int,
    as_of_timestamp: datetime,
    season: int | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> TeamPowerRating | None:
    return calculate_team_ratings(db, as_of_timestamp, season, prior_ratings).get(team_id)


def get_expected_home_margin(
    home_rating: TeamPowerRating,
    away_rating: TeamPowerRating,
    neutral_site: bool,
) -> float:
    home_field = 0.0 if neutral_site else PROVISIONAL_HOME_FIELD_POINTS
    return home_rating.rating - away_rating.rating + home_field


def _require_aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _database_timestamp_as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)