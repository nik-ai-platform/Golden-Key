from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import NormalDist
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.analytics.ncaaf_power_market_shadow import (
    ASSUMED_SPREAD_PRICE,
    PRICE_SOURCE,
    SHADOW_RESIDUAL_SIGMA,
    american_odds_break_even,
    get_latest_pregame_market,
    load_frozen_prior_ratings,
)
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.ncaaf_power_market_shadow_record import (
    NcaafPowerMarketShadowRecord,
)
from app.models.ncaaf_power_market_shadow_result import (
    NcaafPowerMarketShadowResult,
)
from app.services.ncaaf_power_rating_service import MODEL_VERSION
from app.services.ncaaf_power_snapshot_service import (
    RATED,
    calculate_pregame_power_snapshot,
)


SHADOW_SPEC_VERSION = "NCAAF-SHADOW-1.0"
PROSPECTIVE_FROZEN = "PROSPECTIVE_FROZEN"
RETROSPECTIVE_ASOF = "RETROSPECTIVE_ASOF"
CREATED = "CREATED"
REUSED = "REUSED"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
NO_PREGAME_MARKET = "NO_PREGAME_MARKET"
UNKNOWN_NEUTRAL = "UNKNOWN_NEUTRAL"
BEFORE_KICKOFF = "BEFORE_KICKOFF"
NOT_NCAAF = "NOT_NCAAF"
NOT_SETTLED = "NOT_SETTLED"
READINESS_CHECKPOINTS = (25, 50, 100, 250)


class ShadowEvidenceIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ShadowGenerationResult:
    state: str
    game_id: int
    record: NcaafPowerMarketShadowRecord | None = None


@dataclass(frozen=True)
class ShadowGenerationReport:
    season: int
    considered: int
    created: int
    reused: int
    reasons: dict[str, int]


@dataclass(frozen=True)
class ShadowEvaluationResult:
    state: str
    shadow_record_id: int
    result: NcaafPowerMarketShadowResult | None = None


def create_shadow_record_for_game(
    db: Session,
    game_id: int,
    *,
    generated_at: datetime | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> ShadowGenerationResult:
    generated_at = _as_utc(generated_at or datetime.now(UTC), "generated_at")
    game = db.get(Game, game_id)
    if game is None:
        raise LookupError(f"Game {game_id} does not exist")
    if game.sport != "NCAAF":
        return ShadowGenerationResult(NOT_NCAAF, game_id)
    kickoff = _as_utc(game.game_date, "game.game_date")
    if generated_at < kickoff:
        return ShadowGenerationResult(BEFORE_KICKOFF, game_id)
    if game.neutral_site is None:
        return ShadowGenerationResult(UNKNOWN_NEUTRAL, game_id)
    market = get_latest_pregame_market(db, game_id, kickoff)
    if market is None:
        return ShadowGenerationResult(NO_PREGAME_MARKET, game_id)
    if prior_ratings is None:
        prior_ratings, _ = load_frozen_prior_ratings(db)

    calculated = calculate_pregame_power_snapshot(
        db,
        game_id,
        rating_as_of=kickoff,
        prior_ratings=prior_ratings,
    )
    if calculated.state != RATED:
        return ShadowGenerationResult(INSUFFICIENT_HISTORY, game_id)
    if (
        calculated.home_rating is None
        or calculated.away_rating is None
        or calculated.independent_model_margin is None
        or calculated.input_hash is None
        or calculated.rating_input_hash is None
    ):
        raise ShadowEvidenceIntegrityError("Rated shadow calculation is incomplete")

    market_margin = -market.spread_home
    disagreement = calculated.independent_model_margin - market_margin
    p_home_cover = min(
        0.75,
        max(0.25, NormalDist().cdf(disagreement / SHADOW_RESIDUAL_SIGMA)),
    )
    shadow_side = "HOME" if p_home_cover > 0.5 else "AWAY"
    p_selected = p_home_cover if shadow_side == "HOME" else 1.0 - p_home_cover
    break_even = american_odds_break_even(ASSUMED_SPREAD_PRICE)
    minimum_games = min(
        calculated.home_rating.games_used,
        calculated.away_rating.games_used,
    )
    values = {
        "game_id": game.id,
        "power_model_version": MODEL_VERSION,
        "shadow_spec_version": SHADOW_SPEC_VERSION,
        "generation_provenance": (
            RETROSPECTIVE_ASOF
            if authoritative_result_available_as_of(db, game.id, generated_at)
            else PROSPECTIVE_FROZEN
        ),
        "generated_at": generated_at,
        "rating_as_of": kickoff,
        "home_team_id": game.home_team_id,
        "away_team_id": game.away_team_id,
        "neutral_site": bool(game.neutral_site),
        "home_rating": calculated.home_rating.rating,
        "away_rating": calculated.away_rating.rating,
        "home_games_used": calculated.home_rating.games_used,
        "away_games_used": calculated.away_rating.games_used,
        "home_effective_games": calculated.home_rating.effective_games,
        "away_effective_games": calculated.away_rating.effective_games,
        "home_uncertainty": calculated.home_rating.uncertainty,
        "away_uncertainty": calculated.away_rating.uncertainty,
        "combined_uncertainty": math.hypot(
            calculated.home_rating.uncertainty,
            calculated.away_rating.uncertainty,
        ),
        "independent_model_margin": calculated.independent_model_margin,
        "odds_snapshot_id": market.odds_snapshot_id,
        "sportsbook": market.sportsbook,
        "odds_created_at": market.odds_created_at,
        "spread_home": market.spread_home,
        "spread_away": market.spread_away,
        "market_margin": market_margin,
        "disagreement": disagreement,
        "abs_disagreement": abs(disagreement),
        "p_home_cover_shadow": p_home_cover,
        "shadow_side": shadow_side,
        "p_selected_shadow": p_selected,
        "spread_price": ASSUMED_SPREAD_PRICE,
        "price_source": PRICE_SOURCE,
        "break_even_probability": break_even,
        "shadow_edge": p_selected - break_even,
        "evidence_gate_pass": minimum_games >= 4,
        "spread_safety_gate_pass": _spread_safety_gate(
            abs(market_margin),
            p_selected,
            break_even,
        ),
        "power_input_hash": calculated.rating_input_hash,
    }
    existing = _get_shadow_record(db, game.id)
    if existing is not None:
        _require_identical_shadow(existing, values)
        return ShadowGenerationResult(REUSED, game_id, existing)
    record = NcaafPowerMarketShadowRecord(**values)
    db.add(record)
    db.flush()
    return ShadowGenerationResult(CREATED, game_id, record)


def authoritative_result_available_as_of(
    db: Session,
    game_id: int,
    as_of: datetime,
) -> bool:
    as_of = _as_utc(as_of, "as_of")
    cutoff = as_of.replace(tzinfo=None)
    game = db.get(Game, game_id)
    if game is None:
        return False
    persisted_timestamps = (
        game.completed_at,
        game.historical_result_observed_at,
    )
    if any(timestamp is not None and timestamp <= cutoff for timestamp in persisted_timestamps):
        return True
    return bool(
        db.query(
            GameResultObservation.id,
        )
        .filter(
            GameResultObservation.game_id == game_id,
            GameResultObservation.status == "final",
            GameResultObservation.observed_at <= cutoff,
        )
        .first()
    )


def generate_eligible_upcoming_shadow_records(
    db: Session,
    season: int,
    *,
    generated_at: datetime | None = None,
    prior_ratings: dict[int, float] | None = None,
) -> ShadowGenerationReport:
    generated_at = _as_utc(generated_at or datetime.now(UTC), "generated_at")
    cutoff = generated_at.astimezone(UTC).replace(tzinfo=None)
    games = (
        db.query(Game)
        .filter(
            Game.sport == "NCAAF",
            Game.season == season,
            Game.game_date <= cutoff,
        )
        .order_by(Game.game_date, Game.id)
        .all()
    )
    if prior_ratings is None:
        prior_ratings, _ = load_frozen_prior_ratings(db)
    counts: dict[str, int] = {}
    for game in games:
        outcome = create_shadow_record_for_game(
            db,
            game.id,
            generated_at=generated_at,
            prior_ratings=prior_ratings,
        )
        counts[outcome.state] = counts.get(outcome.state, 0) + 1
    return ShadowGenerationReport(
        season=season,
        considered=len(games),
        created=counts.pop(CREATED, 0),
        reused=counts.pop(REUSED, 0),
        reasons=counts,
    )


def evaluate_shadow_record(
    db: Session,
    shadow_record_id: int,
    *,
    settled_at: datetime | None = None,
) -> ShadowEvaluationResult:
    record = db.get(NcaafPowerMarketShadowRecord, shadow_record_id)
    if record is None:
        raise LookupError(f"Shadow record {shadow_record_id} does not exist")
    game = db.get(Game, record.game_id)
    if (
        game is None
        or game.status != "final"
        or game.home_score is None
        or game.away_score is None
    ):
        return ShadowEvaluationResult(NOT_SETTLED, shadow_record_id)
    actual_margin = float(game.home_score - game.away_score)
    model_error = actual_margin - record.independent_model_margin
    market_error = actual_margin - record.market_margin
    values = {
        "shadow_record_id": record.id,
        "home_score": float(game.home_score),
        "away_score": float(game.away_score),
        "actual_home_margin": actual_margin,
        "model_margin_error": model_error,
        "market_margin_error": market_error,
        "model_absolute_error": abs(model_error),
        "market_absolute_error": abs(market_error),
        "settled_at": _as_utc(
            settled_at
            or game.completed_at
            or datetime.now(UTC),
            "settled_at",
        ),
    }
    existing = (
        db.query(NcaafPowerMarketShadowResult)
        .filter(NcaafPowerMarketShadowResult.shadow_record_id == record.id)
        .one_or_none()
    )
    if existing is not None:
        _require_identical_result(existing, values)
        return ShadowEvaluationResult(REUSED, record.id, existing)
    result = NcaafPowerMarketShadowResult(**values)
    db.add(result)
    db.flush()
    return ShadowEvaluationResult(CREATED, record.id, result)


def evaluate_settled_shadow_records(
    db: Session,
    *,
    settled_at: datetime | None = None,
) -> dict[str, int]:
    records = db.query(NcaafPowerMarketShadowRecord).order_by(
        NcaafPowerMarketShadowRecord.id
    )
    counts: dict[str, int] = {}
    for record in records:
        outcome = evaluate_shadow_record(db, record.id, settled_at=settled_at)
        counts[outcome.state] = counts.get(outcome.state, 0) + 1
    return counts


def build_frozen_evidence_report(db: Session) -> dict[str, Any]:
    records = db.query(NcaafPowerMarketShadowRecord).all()
    results = {
        result.shadow_record_id: result
        for result in db.query(NcaafPowerMarketShadowResult).all()
    }
    by_provenance = {}
    for provenance in (PROSPECTIVE_FROZEN, RETROSPECTIVE_ASOF):
        group = [record for record in records if record.generation_provenance == provenance]
        settled = [(record, results[record.id]) for record in group if record.id in results]
        by_provenance[provenance] = _provenance_report(group, settled)
    prospective_settled = by_provenance[PROSPECTIVE_FROZEN]["settled_count"]
    return {
        "shadow_spec_version": SHADOW_SPEC_VERSION,
        "power_model_version": MODEL_VERSION,
        "provenance": by_provenance,
        "readiness_checkpoints": {
            str(checkpoint): {
                "status": (
                    "REVIEW_DUE"
                    if prospective_settled >= checkpoint
                    else "PENDING"
                ),
                "remaining": max(checkpoint - prospective_settled, 0),
            }
            for checkpoint in READINESS_CHECKPOINTS
        },
    }


def _provenance_report(
    records: list[NcaafPowerMarketShadowRecord],
    settled: list[tuple[NcaafPowerMarketShadowRecord, NcaafPowerMarketShadowResult]],
) -> dict[str, Any]:
    return {
        "record_count": len(records),
        "settled_count": len(settled),
        "minimum_games_bands": {
            f">={threshold}": _accuracy_report(
                [
                    item
                    for item in settled
                    if min(item[0].home_games_used, item[0].away_games_used)
                    >= threshold
                ]
            )
            for threshold in range(1, 7)
        },
        "probability_calibration": _probability_calibration(settled),
        "spread_buckets": _evidence_spread_buckets(settled),
        "uncertainty_quartiles": _evidence_uncertainty_quartiles(settled),
        "large_spread_21_5_plus": _evidence_large_spread(settled, 21.5),
        "large_spread_30_5_plus": _evidence_large_spread(settled, 30.5),
    }


def _accuracy_report(
    settled: list[tuple[NcaafPowerMarketShadowRecord, NcaafPowerMarketShadowResult]],
) -> dict[str, Any]:
    if not settled:
        return {"n": 0}
    actual = np.asarray([item[1].actual_home_margin for item in settled], dtype=float)
    model = np.asarray([item[0].independent_model_margin for item in settled], dtype=float)
    market = np.asarray([item[0].market_margin for item in settled], dtype=float)
    return {
        "n": len(settled),
        "model": _prediction_metrics(actual, model),
        "market": _prediction_metrics(actual, market),
    }


def _prediction_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    errors = actual - predicted
    correlation = None
    if len(actual) >= 2 and np.std(actual) > 0 and np.std(predicted) > 0:
        correlation = float(np.corrcoef(actual, predicted)[0, 1])
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(math.sqrt(float(np.mean(errors**2)))),
        "bias": float(np.mean(errors)),
        "correlation": correlation,
    }


def _probability_calibration(
    settled: list[tuple[NcaafPowerMarketShadowRecord, NcaafPowerMarketShadowResult]],
) -> dict[str, Any]:
    resolved = []
    pushes = 0
    for record, result in settled:
        ats_margin = result.actual_home_margin + record.spread_home
        if ats_margin == 0:
            pushes += 1
            continue
        resolved.append((record, 1.0 if ats_margin > 0 else 0.0))
    buckets = ((0.25, 0.35), (0.35, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.7500000001))
    return {
        "n": len(resolved),
        "pushes": pushes,
        "brier_score": (
            float(
                np.mean(
                    [
                        (record.p_home_cover_shadow - outcome) ** 2
                        for record, outcome in resolved
                    ]
                )
            )
            if resolved
            else None
        ),
        "buckets": {
            f"{lower:.2f}-{min(upper, 0.75):.2f}": {
                "n": len(bucket := [
                    item
                    for item in resolved
                    if lower <= item[0].p_home_cover_shadow < upper
                ]),
                "mean_probability": (
                    float(np.mean([item[0].p_home_cover_shadow for item in bucket]))
                    if bucket
                    else None
                ),
                "observed_home_cover_rate": (
                    float(np.mean([item[1] for item in bucket]))
                    if bucket
                    else None
                ),
            }
            for lower, upper in buckets
        },
    }


def _evidence_spread_buckets(
    settled: list[tuple[NcaafPowerMarketShadowRecord, NcaafPowerMarketShadowResult]],
) -> dict[str, Any]:
    definitions = (
        ("0-3", 0.0, 3.5),
        ("3.5-7", 3.5, 7.5),
        ("7.5-10", 7.5, 10.5),
        ("10.5-14", 10.5, 14.5),
        ("14.5-21", 14.5, 21.5),
        ("21.5-30", 21.5, 30.5),
        ("30.5+", 30.5, math.inf),
    )
    return {
        label: _accuracy_report(
            [item for item in settled if lower <= abs(item[0].market_margin) < upper]
        )
        for label, lower, upper in definitions
    }


def _evidence_uncertainty_quartiles(
    settled: list[tuple[NcaafPowerMarketShadowRecord, NcaafPowerMarketShadowResult]],
) -> dict[str, Any]:
    if not settled:
        return {}
    ordered = sorted(settled, key=lambda item: (item[0].combined_uncertainty, item[0].id))
    return {
        f"Q{index}": _accuracy_report([ordered[int(position)] for position in indexes])
        for index, indexes in enumerate(
            np.array_split(np.arange(len(ordered)), min(4, len(ordered))),
            start=1,
        )
        if len(indexes)
    }


def _evidence_large_spread(
    settled: list[tuple[NcaafPowerMarketShadowRecord, NcaafPowerMarketShadowResult]],
    threshold: float,
) -> dict[str, Any]:
    selected = [item for item in settled if abs(item[0].market_margin) >= threshold]
    return {
        "threshold": threshold,
        "accuracy": _accuracy_report(selected),
        "shadow_record_ids": [item[0].id for item in selected],
    }


def _get_shadow_record(
    db: Session,
    game_id: int,
) -> NcaafPowerMarketShadowRecord | None:
    return (
        db.query(NcaafPowerMarketShadowRecord)
        .filter(
            NcaafPowerMarketShadowRecord.game_id == game_id,
            NcaafPowerMarketShadowRecord.power_model_version == MODEL_VERSION,
            NcaafPowerMarketShadowRecord.shadow_spec_version == SHADOW_SPEC_VERSION,
        )
        .one_or_none()
    )


def _spread_safety_gate(
    absolute_market_margin: float,
    selected_probability: float,
    break_even_probability: float,
) -> bool:
    if absolute_market_margin <= 21.0:
        return selected_probability >= break_even_probability + 0.02
    if absolute_market_margin <= 30.0:
        return selected_probability >= break_even_probability + 0.04
    return False


def _require_identical_shadow(
    record: NcaafPowerMarketShadowRecord,
    values: dict[str, Any],
) -> None:
    excluded = {"generated_at", "generation_provenance"}
    mismatches = [
        field
        for field, expected in values.items()
        if field not in excluded and not _values_match(getattr(record, field), expected)
    ]
    if mismatches:
        raise ShadowEvidenceIntegrityError(
            f"Existing shadow record conflicts in fields: {', '.join(mismatches)}"
        )


def _require_identical_result(
    result: NcaafPowerMarketShadowResult,
    values: dict[str, Any],
) -> None:
    mismatches = [
        field
        for field, expected in values.items()
        if field != "settled_at" and not _values_match(getattr(result, field), expected)
    ]
    if mismatches:
        raise ShadowEvidenceIntegrityError(
            f"Existing shadow result conflicts in fields: {', '.join(mismatches)}"
        )


def _values_match(actual: Any, expected: Any) -> bool:
    if isinstance(expected, datetime):
        return _as_utc(actual, "stored timestamp") == _as_utc(expected, "timestamp")
    if isinstance(expected, float):
        return math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1e-12)
    return actual == expected


def _as_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)