from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.prediction_power_snapshot import PredictionPowerSnapshot
from app.models.team_power_rating import TeamPowerRatingRecord
from app.services.ncaaf_power_rating_service import (
    MODEL_VERSION,
    MOV_LINEAR_THRESHOLD,
    MOV_LOG_SCALE,
    PRIOR_PSEUDO_GAMES,
    PRIOR_REGRESSION,
    PROVISIONAL_HOME_FIELD_POINTS,
    RECENCY_HALF_LIFE_DAYS,
    RatingCalculation,
    TeamPowerRating,
    calculate_rating_result,
    get_expected_home_margin,
)


RATED = "RATED"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


class PowerSnapshotIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredTeamRatings:
    calculation: RatingCalculation
    records: dict[int, TeamPowerRatingRecord]
    input_hash: str
    source_max_observed_at: datetime


@dataclass(frozen=True)
class PregamePowerSnapshotResult:
    state: str
    snapshot: PredictionPowerSnapshot | None
    missing_team_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class CalculatedPregamePowerSnapshot:
    state: str
    game_id: int
    model_version: str
    rating_as_of: datetime
    home_team_id: int
    away_team_id: int
    home_rating: TeamPowerRating | None
    away_rating: TeamPowerRating | None
    neutral_site: bool
    home_field_points: float
    independent_model_margin: float | None
    source_max_observed_at: datetime | None
    training_game_count: int
    input_hash: str | None
    rating_input_hash: str | None
    rating_calculation: RatingCalculation
    missing_team_ids: tuple[int, ...] = ()


def calculate_and_store_team_ratings(
    db: Session,
    *,
    season: int,
    rating_as_of: datetime,
    prior_ratings: dict[int, float] | None = None,
) -> StoredTeamRatings:
    rating_as_of = _as_utc(rating_as_of, "rating_as_of")
    calculation, input_hash, source_max_observed_at = _calculate_rating_provenance(
        db,
        season,
        rating_as_of,
        prior_ratings,
    )
    if input_hash is None or source_max_observed_at is None:
        raise ValueError("No eligible NCAAF history exists at rating_as_of")
    records = _store_rating_calculation(
        db,
        calculation,
        season,
        rating_as_of,
        source_max_observed_at,
        input_hash,
    )
    db.flush()
    return StoredTeamRatings(
        calculation=calculation,
        records=records,
        input_hash=input_hash,
        source_max_observed_at=source_max_observed_at,
    )


def calculate_pregame_power_snapshot(
    db: Session,
    game_id: int,
    *,
    rating_as_of: datetime | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> CalculatedPregamePowerSnapshot:
    game, rating_as_of = _validated_target_game(db, game_id, rating_as_of)
    calculation, rating_input_hash, source_max_observed_at = (
        _calculate_rating_provenance(
            db,
            game.season,
            rating_as_of,
            prior_ratings,
        )
    )
    ratings = calculation.ratings
    missing_team_ids = tuple(
        team_id
        for team_id in (game.home_team_id, game.away_team_id)
        if team_id not in ratings
    )
    home_field_points = 0.0 if game.neutral_site else PROVISIONAL_HOME_FIELD_POINTS
    if missing_team_ids:
        return CalculatedPregamePowerSnapshot(
            state=INSUFFICIENT_HISTORY,
            game_id=game.id,
            model_version=MODEL_VERSION,
            rating_as_of=rating_as_of,
            home_team_id=game.home_team_id,
            away_team_id=game.away_team_id,
            home_rating=ratings.get(game.home_team_id),
            away_rating=ratings.get(game.away_team_id),
            neutral_site=game.neutral_site,
            home_field_points=home_field_points,
            independent_model_margin=None,
            source_max_observed_at=source_max_observed_at,
            training_game_count=len(calculation.eligible_games),
            input_hash=None,
            rating_input_hash=rating_input_hash,
            rating_calculation=calculation,
            missing_team_ids=missing_team_ids,
        )

    home_rating = ratings[game.home_team_id]
    away_rating = ratings[game.away_team_id]
    independent_model_margin = get_expected_home_margin(
        home_rating,
        away_rating,
        game.neutral_site,
    )
    return CalculatedPregamePowerSnapshot(
        state=RATED,
        game_id=game.id,
        model_version=MODEL_VERSION,
        rating_as_of=rating_as_of,
        home_team_id=game.home_team_id,
        away_team_id=game.away_team_id,
        home_rating=home_rating,
        away_rating=away_rating,
        neutral_site=game.neutral_site,
        home_field_points=home_field_points,
        independent_model_margin=independent_model_margin,
        source_max_observed_at=source_max_observed_at,
        training_game_count=len(calculation.eligible_games),
        input_hash=_snapshot_input_hash(
            rating_input_hash,
            game,
            rating_as_of,
            home_field_points,
        ),
        rating_input_hash=rating_input_hash,
        rating_calculation=calculation,
    )


def _store_rating_calculation(
    db: Session,
    calculation: RatingCalculation,
    season: int,
    rating_as_of: datetime,
    source_max_observed_at: datetime,
    input_hash: str,
) -> dict[int, TeamPowerRatingRecord]:
    values_by_team = {
        team_id: {
            "sport": "NCAAF",
            "season": season,
            "team_id": team_id,
            "model_version": MODEL_VERSION,
            "rating": rating.rating,
            "uncertainty": rating.uncertainty,
            "games_used": rating.games_used,
            "effective_games": rating.effective_games,
            "rating_as_of": rating_as_of,
            "source_max_observed_at": source_max_observed_at,
            "training_game_count": len(calculation.eligible_games),
            "input_hash": input_hash,
        }
        for team_id, rating in calculation.ratings.items()
    }
    records = {
        team_id: _store_team_rating(db, values)
        for team_id, values in values_by_team.items()
    }
    return records


def create_pregame_power_snapshot(
    db: Session,
    game_id: int,
    *,
    rating_as_of: datetime | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> PregamePowerSnapshotResult:
    calculated = calculate_pregame_power_snapshot(
        db,
        game_id,
        rating_as_of=rating_as_of,
        prior_ratings=prior_ratings,
    )
    if calculated.state == INSUFFICIENT_HISTORY:
        return PregamePowerSnapshotResult(
            state=INSUFFICIENT_HISTORY,
            snapshot=None,
            missing_team_ids=calculated.missing_team_ids,
        )
    if (
        calculated.home_rating is None
        or calculated.away_rating is None
        or calculated.source_max_observed_at is None
        or calculated.input_hash is None
        or calculated.rating_input_hash is None
    ):
        raise PowerSnapshotIntegrityError("Rated snapshot calculation is incomplete")

    game = db.get(Game, game_id)
    if game is None or game.season is None:
        raise PowerSnapshotIntegrityError("Target game disappeared during calculation")
    records = _store_rating_calculation(
        db,
        calculated.rating_calculation,
        game.season,
        calculated.rating_as_of,
        calculated.source_max_observed_at,
        calculated.rating_input_hash,
    )
    values = {
        "game_id": calculated.game_id,
        "model_version": MODEL_VERSION,
        "rating_as_of": calculated.rating_as_of,
        "home_team_id": calculated.home_team_id,
        "away_team_id": calculated.away_team_id,
        "home_rating": calculated.home_rating.rating,
        "away_rating": calculated.away_rating.rating,
        "home_uncertainty": calculated.home_rating.uncertainty,
        "away_uncertainty": calculated.away_rating.uncertainty,
        "home_games_used": calculated.home_rating.games_used,
        "away_games_used": calculated.away_rating.games_used,
        "home_effective_games": calculated.home_rating.effective_games,
        "away_effective_games": calculated.away_rating.effective_games,
        "minimum_games_used": min(
            calculated.home_rating.games_used,
            calculated.away_rating.games_used,
        ),
        "combined_uncertainty": math.hypot(
            calculated.home_rating.uncertainty,
            calculated.away_rating.uncertainty,
        ),
        "neutral_site": calculated.neutral_site,
        "home_field_points": calculated.home_field_points,
        "independent_model_margin": calculated.independent_model_margin,
        "source_max_observed_at": calculated.source_max_observed_at,
        "training_game_count": calculated.training_game_count,
        "input_hash": calculated.input_hash,
    }
    snapshot = _store_power_snapshot(db, values)
    db.flush()
    if set(records) != set(calculated.rating_calculation.ratings):
        raise PowerSnapshotIntegrityError("Not all calculated team ratings were stored")
    return PregamePowerSnapshotResult(state=RATED, snapshot=snapshot)


def get_power_snapshot(
    db: Session,
    game_id: int,
    rating_as_of: datetime,
    model_version: str = MODEL_VERSION,
) -> PredictionPowerSnapshot | None:
    rating_as_of = _as_utc(rating_as_of, "rating_as_of")
    return (
        db.query(PredictionPowerSnapshot)
        .filter(
            PredictionPowerSnapshot.game_id == game_id,
            PredictionPowerSnapshot.model_version == model_version,
            PredictionPowerSnapshot.rating_as_of == rating_as_of,
        )
        .one_or_none()
    )


def _validated_target_game(
    db: Session,
    game_id: int,
    rating_as_of: datetime | None,
) -> tuple[Game, datetime]:
    game = db.get(Game, game_id)
    if game is None:
        raise LookupError(f"Game {game_id} does not exist")
    if game.sport != "NCAAF":
        raise ValueError("Power snapshots are only supported for NCAAF games")
    if game.season is None:
        raise ValueError("NCAAF game must have a season")
    if game.neutral_site is None:
        raise ValueError("NCAAF game must have a known neutral-site value")

    kickoff = _as_utc(game.game_date, "game.game_date")
    rating_as_of = kickoff if rating_as_of is None else _as_utc(rating_as_of, "rating_as_of")
    if rating_as_of > kickoff:
        raise ValueError("rating_as_of must not be later than game kickoff")
    return game, rating_as_of


def _calculate_rating_provenance(
    db: Session,
    season: int,
    rating_as_of: datetime,
    prior_ratings: dict[int, float] | None,
) -> tuple[RatingCalculation, str | None, datetime | None]:
    calculation = calculate_rating_result(db, rating_as_of, season, prior_ratings)
    if not calculation.eligible_games:
        return calculation, None, None
    input_hash = _rating_input_hash(calculation, season, rating_as_of, prior_ratings)
    source_max_observed_at = max(
        game.observation_observed_at for game in calculation.eligible_games
    )
    return calculation, input_hash, source_max_observed_at


def _store_team_rating(db: Session, values: dict[str, Any]) -> TeamPowerRatingRecord:
    existing = (
        db.query(TeamPowerRatingRecord)
        .filter(
            TeamPowerRatingRecord.team_id == values["team_id"],
            TeamPowerRatingRecord.model_version == values["model_version"],
            TeamPowerRatingRecord.rating_as_of == values["rating_as_of"],
        )
        .one_or_none()
    )
    if existing is not None:
        _require_identical(existing, values, "team rating")
        return existing
    record = TeamPowerRatingRecord(**values)
    db.add(record)
    return record


def _store_power_snapshot(db: Session, values: dict[str, Any]) -> PredictionPowerSnapshot:
    existing = (
        db.query(PredictionPowerSnapshot)
        .filter(
            PredictionPowerSnapshot.game_id == values["game_id"],
            PredictionPowerSnapshot.model_version == values["model_version"],
            PredictionPowerSnapshot.rating_as_of == values["rating_as_of"],
        )
        .one_or_none()
    )
    if existing is not None:
        _require_identical(existing, values, "pregame power snapshot")
        return existing
    snapshot = PredictionPowerSnapshot(**values)
    db.add(snapshot)
    return snapshot


def _require_identical(record: Any, values: dict[str, Any], label: str) -> None:
    mismatches = []
    for field, expected in values.items():
        actual = getattr(record, field)
        if isinstance(expected, datetime):
            matches = _as_utc(actual, field) == _as_utc(expected, field)
        elif isinstance(expected, float):
            matches = math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)
        else:
            matches = actual == expected
        if not matches:
            mismatches.append(field)
    if mismatches:
        raise PowerSnapshotIntegrityError(
            f"Existing {label} conflicts in fields: {', '.join(mismatches)}"
        )


def _rating_input_hash(
    calculation: RatingCalculation,
    season: int,
    rating_as_of: datetime,
    prior_ratings: dict[int, float] | None,
) -> str:
    payload = {
        "model": {
            "version": MODEL_VERSION,
            "recency_half_life_days": RECENCY_HALF_LIFE_DAYS,
            "home_field_points": PROVISIONAL_HOME_FIELD_POINTS,
            "mov_linear_threshold": MOV_LINEAR_THRESHOLD,
            "mov_log_scale": MOV_LOG_SCALE,
            "prior_regression": PRIOR_REGRESSION,
            "prior_pseudo_games": PRIOR_PSEUDO_GAMES,
        },
        "season": season,
        "rating_as_of": _canonical_datetime(rating_as_of),
        "prior_ratings": [
            [team_id, _canonical_float(rating)]
            for team_id, rating in sorted((prior_ratings or {}).items())
        ],
        "games": [
            {
                "game_id": game.game_id,
                "kickoff": _canonical_datetime(game.game_date),
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "neutral_site": game.neutral_site,
                "home_score": _canonical_float(game.home_score),
                "away_score": _canonical_float(game.away_score),
                "observation_id": game.observation_id,
                "observation_provider": game.observation_provider,
                "observation_observed_at": _canonical_datetime(
                    game.observation_observed_at
                ),
                "observation_source_updated_at": (
                    _canonical_datetime(game.observation_source_updated_at)
                    if game.observation_source_updated_at is not None
                    else None
                ),
                "observation_payload_hash": game.observation_payload_hash,
            }
            for game in calculation.eligible_games
        ],
    }
    return _hash_payload(payload)


def _snapshot_input_hash(
    rating_input_hash: str,
    game: Game,
    rating_as_of: datetime,
    home_field_points: float,
) -> str:
    return _hash_payload(
        {
            "rating_input_hash": rating_input_hash,
            "model_version": MODEL_VERSION,
            "game_id": game.id,
            "kickoff": _canonical_datetime(_as_utc(game.game_date, "game.game_date")),
            "rating_as_of": _canonical_datetime(rating_as_of),
            "home_team_id": game.home_team_id,
            "away_team_id": game.away_team_id,
            "neutral_site": game.neutral_site,
            "home_field_points": _canonical_float(home_field_points),
        }
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_datetime(value: datetime) -> str:
    return _as_utc(value, "timestamp").isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _canonical_float(value: float) -> str:
    return format(float(value), ".17g")


def _as_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)