from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import NormalDist
from typing import Any

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.models.team_power_rating import TeamPowerRatingRecord
from app.services.ncaaf_power_rating_service import MODEL_VERSION
from app.services.ncaaf_power_snapshot_service import (
    RATED,
    calculate_pregame_power_snapshot,
)


SHADOW_RESIDUAL_SIGMA = 19.0
ASSUMED_SPREAD_PRICE = -110
PRICE_SOURCE = "PRICE_ASSUMED_-110"


@dataclass(frozen=True)
class PregameMarket:
    odds_snapshot_id: int
    sportsbook: str | None
    odds_created_at: datetime
    spread_home: float
    spread_away: float | None


@dataclass(frozen=True)
class ShadowRow:
    game_id: int
    kickoff: datetime
    home_team: str
    away_team: str
    neutral_site: bool
    home_rating: float
    away_rating: float
    home_games_used: int
    away_games_used: int
    home_uncertainty: float
    away_uncertainty: float
    combined_uncertainty: float
    independent_model_margin: float
    odds_snapshot_id: int
    sportsbook: str | None
    odds_created_at: datetime
    spread_home: float
    spread_away: float | None
    market_margin: float
    disagreement: float
    abs_disagreement: float
    settled: bool
    actual_home_margin: float | None
    model_margin_error: float | None
    market_margin_error: float | None
    input_hash: str
    training_game_ids: tuple[int, ...]
    training_observed_ats: tuple[datetime, ...]

    @property
    def minimum_games_used(self) -> int:
        return min(self.home_games_used, self.away_games_used)


@dataclass(frozen=True)
class ShadowUniverse:
    rows: tuple[ShadowRow, ...]
    total_games: int
    games_with_pregame_spread: int
    games_with_power_rating: int
    games_with_both: int
    insufficient_history: int
    no_pregame_market: int
    unknown_neutral: int
    settled_eligible_rows: int
    future_eligible_rows: int
    prior_rating_as_of: datetime
    prior_team_count: int


def get_latest_pregame_market(
    db: Session,
    game_id: int,
    kickoff: datetime,
) -> PregameMarket | None:
    cutoff = _as_utc(kickoff).replace(tzinfo=None)
    odds = (
        db.query(Odds)
        .filter(
            Odds.game_id == game_id,
            Odds.spread_home.isnot(None),
            Odds.created_at < cutoff,
        )
        .order_by(Odds.created_at.desc(), Odds.id.desc())
        .first()
    )
    if odds is None:
        return None
    return PregameMarket(
        odds_snapshot_id=odds.id,
        sportsbook=odds.sportsbook,
        odds_created_at=_as_utc(odds.created_at),
        spread_home=float(odds.spread_home),
        spread_away=(float(odds.spread_away) if odds.spread_away is not None else None),
    )


def load_frozen_prior_ratings(
    db: Session,
    prior_season: int = 2025,
) -> tuple[dict[int, float], datetime]:
    rating_as_of = (
        db.query(func.max(TeamPowerRatingRecord.rating_as_of))
        .filter(
            TeamPowerRatingRecord.sport == "NCAAF",
            TeamPowerRatingRecord.season == prior_season,
            TeamPowerRatingRecord.model_version == MODEL_VERSION,
        )
        .scalar()
    )
    if rating_as_of is None:
        raise ValueError(f"No frozen {prior_season} {MODEL_VERSION} prior exists")
    records = (
        db.query(TeamPowerRatingRecord)
        .filter(
            TeamPowerRatingRecord.sport == "NCAAF",
            TeamPowerRatingRecord.season == prior_season,
            TeamPowerRatingRecord.model_version == MODEL_VERSION,
            TeamPowerRatingRecord.rating_as_of == rating_as_of,
        )
        .all()
    )
    input_hashes = {record.input_hash for record in records}
    if len(input_hashes) != 1:
        raise ValueError("Frozen prior rows do not share one input hash")
    return (
        {record.team_id: float(record.rating) for record in records},
        _as_utc(rating_as_of),
    )


def build_shadow_universe(
    db: Session,
    *,
    season: int = 2026,
    prior_ratings: dict[int, float] | None = None,
    prior_rating_as_of: datetime | None = None,
    audit_as_of: datetime | None = None,
) -> ShadowUniverse:
    if prior_ratings is None:
        prior_ratings, loaded_as_of = load_frozen_prior_ratings(db)
        prior_rating_as_of = loaded_as_of
    if prior_rating_as_of is None:
        prior_rating_as_of = datetime(2025, 12, 31, tzinfo=UTC)
    audit_as_of = _as_utc(audit_as_of or datetime.now(UTC))
    games = (
        db.query(Game)
        .filter(Game.sport == "NCAAF", Game.season == season)
        .order_by(Game.game_date, Game.id)
        .all()
    )
    team_ids = {
        team_id
        for game in games
        for team_id in (game.home_team_id, game.away_team_id)
    }
    team_names = {
        team.id: team.name
        for team in db.query(Team).filter(Team.id.in_(team_ids)).all()
    }
    rows = []
    games_with_market = 0
    games_with_power = 0
    games_with_both = 0
    insufficient_history = 0
    no_pregame_market = 0
    unknown_neutral = 0

    for game in games:
        kickoff = _as_utc(game.game_date)
        market = get_latest_pregame_market(db, game.id, kickoff)
        if market is None:
            no_pregame_market += 1
        else:
            games_with_market += 1
        if game.neutral_site is None:
            unknown_neutral += 1
            continue
        calculated = calculate_pregame_power_snapshot(
            db,
            game.id,
            rating_as_of=kickoff,
            prior_ratings=prior_ratings,
        )
        if calculated.state != RATED:
            insufficient_history += 1
            continue
        games_with_power += 1
        if market is None:
            continue
        games_with_both += 1
        if (
            calculated.home_rating is None
            or calculated.away_rating is None
            or calculated.independent_model_margin is None
            or calculated.input_hash is None
        ):
            raise ValueError("Rated shadow calculation is incomplete")
        market_margin = -market.spread_home
        disagreement = calculated.independent_model_margin - market_margin
        settled = (
            game.status == "final"
            and game.home_score is not None
            and game.away_score is not None
        )
        actual_home_margin = (
            float(game.home_score - game.away_score) if settled else None
        )
        rows.append(
            ShadowRow(
                game_id=game.id,
                kickoff=kickoff,
                home_team=team_names[game.home_team_id],
                away_team=team_names[game.away_team_id],
                neutral_site=bool(game.neutral_site),
                home_rating=calculated.home_rating.rating,
                away_rating=calculated.away_rating.rating,
                home_games_used=calculated.home_rating.games_used,
                away_games_used=calculated.away_rating.games_used,
                home_uncertainty=calculated.home_rating.uncertainty,
                away_uncertainty=calculated.away_rating.uncertainty,
                combined_uncertainty=math.hypot(
                    calculated.home_rating.uncertainty,
                    calculated.away_rating.uncertainty,
                ),
                independent_model_margin=calculated.independent_model_margin,
                odds_snapshot_id=market.odds_snapshot_id,
                sportsbook=market.sportsbook,
                odds_created_at=market.odds_created_at,
                spread_home=market.spread_home,
                spread_away=market.spread_away,
                market_margin=market_margin,
                disagreement=disagreement,
                abs_disagreement=abs(disagreement),
                settled=settled,
                actual_home_margin=actual_home_margin,
                model_margin_error=(
                    actual_home_margin - calculated.independent_model_margin
                    if actual_home_margin is not None
                    else None
                ),
                market_margin_error=(
                    actual_home_margin - market_margin
                    if actual_home_margin is not None
                    else None
                ),
                input_hash=calculated.input_hash,
                training_game_ids=tuple(
                    item.game_id for item in calculated.rating_calculation.eligible_games
                ),
                training_observed_ats=tuple(
                    item.observation_observed_at
                    for item in calculated.rating_calculation.eligible_games
                ),
            )
        )

    settled_count = sum(row.settled for row in rows)
    future_count = sum(not row.settled and row.kickoff > audit_as_of for row in rows)
    return ShadowUniverse(
        rows=tuple(rows),
        total_games=len(games),
        games_with_pregame_spread=games_with_market,
        games_with_power_rating=games_with_power,
        games_with_both=games_with_both,
        insufficient_history=insufficient_history,
        no_pregame_market=no_pregame_market,
        unknown_neutral=unknown_neutral,
        settled_eligible_rows=settled_count,
        future_eligible_rows=future_count,
        prior_rating_as_of=_as_utc(prior_rating_as_of),
        prior_team_count=len(prior_ratings),
    )


def build_shadow_report(db: Session, universe: ShadowUniverse) -> dict[str, Any]:
    rows = list(universe.rows)
    settled = [row for row in rows if row.settled]
    probabilities = [_probability_row(row) for row in rows]
    return {
        "metadata": {
            "model_version": MODEL_VERSION,
            "prior_rating_as_of": universe.prior_rating_as_of.isoformat(),
            "prior_team_count": universe.prior_team_count,
            "residual_sigma": SHADOW_RESIDUAL_SIGMA,
            "price_source": PRICE_SOURCE,
        },
        "A_coverage": {
            "total_2026_games": universe.total_games,
            "games_with_pregame_spread": universe.games_with_pregame_spread,
            "games_with_power_rating": universe.games_with_power_rating,
            "games_with_both": universe.games_with_both,
            "INSUFFICIENT_HISTORY": universe.insufficient_history,
            "NO_PREGAME_MARKET": universe.no_pregame_market,
            "unknown_neutral": universe.unknown_neutral,
            "eligible_shadow_rows": len(rows),
            "settled_eligible_rows": universe.settled_eligible_rows,
            "future_eligible_rows": universe.future_eligible_rows,
        },
        "B_disagreement_distribution": _distribution(
            [row.disagreement for row in rows]
        )
        | {"abs_disagreement_buckets": _abs_disagreement_buckets(rows)},
        "C_spread_buckets": _spread_buckets(rows),
        "D_favorite_underdog_direction": _direction_summary(rows),
        "E_npi_4_0_comparison": _npi_comparison(db, rows),
        "F_settled_margin_accuracy": _accuracy(settled),
        "G_disagreement_vs_accuracy": _disagreement_accuracy(settled),
        "H_evidence_thresholds": _evidence_thresholds(settled),
        "I_uncertainty": _uncertainty_quartiles(settled),
        "J_21_5_plus_audit": _large_spread_audit(settled, 21.5),
        "K_30_5_plus_audit": _large_spread_audit(settled, 30.5),
        "L_shadow_probability_distribution": _probability_distribution(
            probabilities
        ),
        "M_price_aware_edge": _edge_distribution(probabilities),
        "N_safety_gate_funnel": _safety_funnel(probabilities),
    }


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    array = np.asarray(values, dtype=float)
    median = float(np.median(array))
    return {
        "n": len(values),
        "mean": float(np.mean(array)),
        "median": median,
        "sd": float(np.std(array)),
        "mad_equivalent": float(1.4826 * np.median(np.abs(array - median))),
        "percentiles": {
            str(percentile): float(np.percentile(array, percentile))
            for percentile in (5, 10, 25, 50, 75, 90, 95)
        },
    }


def _abs_disagreement_buckets(rows: list[ShadowRow]) -> dict[str, Any]:
    definitions = (
        ("0-3", 0.0, 3.0),
        ("3-7", 3.0, 7.0),
        ("7-14", 7.0, 14.0),
        ("14-21", 14.0, 21.0),
        ("21+", 21.0, math.inf),
    )
    return _bucket_counts(rows, definitions, lambda row: row.abs_disagreement)


def _spread_buckets(rows: list[ShadowRow]) -> dict[str, Any]:
    definitions = (
        ("0-3", 0.0, 3.5),
        ("3.5-7", 3.5, 7.5),
        ("7.5-10", 7.5, 10.5),
        ("10.5-14", 10.5, 14.5),
        ("14.5-21", 14.5, 21.5),
        ("21.5-30", 21.5, 30.5),
        ("30.5+", 30.5, math.inf),
    )
    result = {}
    for label, lower, upper in definitions:
        bucket = [row for row in rows if lower <= abs(row.market_margin) < upper]
        result[label] = {
            "n": len(bucket),
            "average_model_margin": _mean(
                [row.independent_model_margin for row in bucket]
            ),
            "average_market_margin": _mean([row.market_margin for row in bucket]),
            "average_signed_disagreement": _mean(
                [row.disagreement for row in bucket]
            ),
            "average_absolute_disagreement": _mean(
                [row.abs_disagreement for row in bucket]
            ),
            "median_disagreement": _median([row.disagreement for row in bucket]),
            "average_combined_uncertainty": _mean(
                [row.combined_uncertainty for row in bucket]
            ),
        }
    return result


def _direction_summary(rows: list[ShadowRow]) -> dict[str, Any]:
    market_groups = {
        "HOME_FAVORITE": [row for row in rows if row.market_margin > 0],
        "HOME_UNDERDOG": [row for row in rows if row.market_margin < 0],
        "PICKEM": [row for row in rows if row.market_margin == 0],
    }
    return {
        "market_home_side": {
            label: {
                "n": len(group),
                "mean_disagreement": _mean([row.disagreement for row in group]),
                "median_disagreement": _median([row.disagreement for row in group]),
                "mean_abs_disagreement": _mean(
                    [row.abs_disagreement for row in group]
                ),
            }
            for label, group in market_groups.items()
        },
        "model_disagreement_direction": {
            "MODEL_MORE_HOME": sum(row.disagreement > 0 for row in rows),
            "MODEL_MORE_AWAY": sum(row.disagreement < 0 for row in rows),
            "EQUAL": sum(row.disagreement == 0 for row in rows),
        },
    }


def _npi_comparison(db: Session, rows: list[ShadowRow]) -> dict[str, Any]:
    row_by_game = {row.game_id: row for row in rows}
    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.game_id.in_(row_by_game),
            Prediction.model_version == "NPI-4.0",
            Prediction.market == "spread",
        )
        .order_by(Prediction.game_id, Prediction.created_at.desc(), Prediction.id.desc())
        .all()
    )
    selected = {}
    for prediction in predictions:
        row = row_by_game[prediction.game_id]
        if prediction.created_at is not None and _as_utc(prediction.created_at) >= row.kickoff:
            continue
        selected.setdefault(prediction.game_id, prediction)
    counts = {"HOME": 0, "AWAY": 0, "PASS": 0, "OTHER": 0}
    giant_underdogs = []
    records = []
    for game_id, prediction in selected.items():
        row = row_by_game[game_id]
        selection = (prediction.selection or "").upper()
        counts[selection if selection in counts else "OTHER"] += 1
        record = {
            "game_id": game_id,
            "selection": selection,
            "selected_spread": prediction.line_value,
            "probability": prediction.win_probability,
            "confidence": prediction.confidence_score,
            "projected_edge": prediction.projected_edge,
            "independent_model_margin": row.independent_model_margin,
            "market_margin": row.market_margin,
            "disagreement": row.disagreement,
        }
        records.append(record)
        if (
            selection in {"HOME", "AWAY"}
            and prediction.line_value is not None
            and float(prediction.line_value) >= 21.5
        ):
            supports = (
                row.disagreement > 0 if selection == "HOME" else row.disagreement < 0
            )
            giant_underdogs.append(
                record
                | {
                    "home_team": row.home_team,
                    "away_team": row.away_team,
                    "combined_uncertainty": row.combined_uncertainty,
                    "supports_selected_underdog": supports,
                }
            )
    return {
        "n": len(records),
        "selection_counts": counts,
        "giant_underdog_selection_count": len(giant_underdogs),
        "giant_underdog_supported_count": sum(
            item["supports_selected_underdog"] for item in giant_underdogs
        ),
        "giant_underdog_selections": giant_underdogs,
    }


def _accuracy(rows: list[ShadowRow]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    actual = np.asarray([row.actual_home_margin for row in rows], dtype=float)
    model = np.asarray([row.independent_model_margin for row in rows], dtype=float)
    market = np.asarray([row.market_margin for row in rows], dtype=float)
    return {
        "n": len(rows),
        "model": _metric_set(actual, model),
        "market": _metric_set(actual, market),
    }


def _metric_set(actual: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    errors = actual - predicted
    correlation = None
    if len(actual) >= 2 and np.std(actual) > 0 and np.std(predicted) > 0:
        correlation = float(np.corrcoef(actual, predicted)[0, 1])
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(math.sqrt(float(np.mean(errors**2)))),
        "mean_signed_error": float(np.mean(errors)),
        "correlation": correlation,
    }


def _disagreement_accuracy(rows: list[ShadowRow]) -> dict[str, Any]:
    definitions = (
        ("0-3", 0.0, 3.0),
        ("3-7", 3.0, 7.0),
        ("7-14", 7.0, 14.0),
        ("14-21", 14.0, 21.0),
        ("21+", 21.0, math.inf),
    )
    return {
        label: _accuracy(
            [row for row in rows if lower <= row.abs_disagreement < upper]
        )
        for label, lower, upper in definitions
    }


def _evidence_thresholds(rows: list[ShadowRow]) -> dict[str, Any]:
    denominator = len(rows)
    result = {}
    for threshold in range(1, 7):
        eligible = [row for row in rows if row.minimum_games_used >= threshold]
        metrics = _accuracy(eligible)
        result[f">={threshold}"] = metrics | {
            "coverage": len(eligible) / denominator if denominator else 0.0,
            "bias": metrics.get("model", {}).get("mean_signed_error"),
            "correlation": metrics.get("model", {}).get("correlation"),
        }
    return result


def _uncertainty_quartiles(rows: list[ShadowRow]) -> dict[str, Any]:
    if not rows:
        return {}
    ordered = sorted(rows, key=lambda row: (row.combined_uncertainty, row.game_id))
    result = {}
    for index, indexes in enumerate(np.array_split(np.arange(len(ordered)), 4), start=1):
        bucket = [ordered[int(item)] for item in indexes]
        if not bucket:
            continue
        accuracy = _accuracy(bucket)
        result[f"Q{index}"] = accuracy | {
            "minimum_uncertainty": min(row.combined_uncertainty for row in bucket),
            "maximum_uncertainty": max(row.combined_uncertainty for row in bucket),
            "model_bias": accuracy["model"]["mean_signed_error"],
            "mean_abs_disagreement": _mean(
                [row.abs_disagreement for row in bucket]
            ),
        }
    return result


def _large_spread_audit(rows: list[ShadowRow], threshold: float) -> dict[str, Any]:
    selected = [row for row in rows if abs(row.market_margin) >= threshold]
    return {
        "threshold": threshold,
        "summary": _accuracy(selected),
        "games": [
            {
                "game_id": row.game_id,
                "kickoff": row.kickoff.isoformat(),
                "home_team": row.home_team,
                "away_team": row.away_team,
                "market_spread_home": row.spread_home,
                "market_margin": row.market_margin,
                "independent_model_margin": row.independent_model_margin,
                "disagreement": row.disagreement,
                "home_games_used": row.home_games_used,
                "away_games_used": row.away_games_used,
                "combined_uncertainty": row.combined_uncertainty,
                "actual_home_margin": row.actual_home_margin,
                "model_margin_error": row.model_margin_error,
                "market_margin_error": row.market_margin_error,
            }
            for row in selected
        ],
    }


def _probability_row(row: ShadowRow) -> dict[str, Any]:
    home_cover_raw = NormalDist().cdf(row.disagreement / SHADOW_RESIDUAL_SIGMA)
    home_cover = min(0.75, max(0.25, home_cover_raw))
    side = "HOME" if home_cover > 0.5 else "AWAY"
    selected_probability = home_cover if side == "HOME" else 1.0 - home_cover
    break_even = american_odds_break_even(ASSUMED_SPREAD_PRICE)
    return {
        "row": row,
        "shadow_side": side,
        "home_cover_probability_raw": home_cover_raw,
        "home_cover_probability": home_cover,
        "selected_probability": selected_probability,
        "price": ASSUMED_SPREAD_PRICE,
        "price_source": PRICE_SOURCE,
        "break_even_probability": break_even,
        "shadow_edge": selected_probability - break_even,
    }


def american_odds_break_even(price: int | float) -> float:
    price = float(price)
    if price == 0:
        raise ValueError("American odds cannot be zero")
    if price < 0:
        return abs(price) / (abs(price) + 100.0)
    return 100.0 / (price + 100.0)


def _probability_distribution(probabilities: list[dict[str, Any]]) -> dict[str, Any]:
    values = [item["selected_probability"] for item in probabilities]
    buckets = (
        ("50-54", 0.50, 0.54),
        ("54-56", 0.54, 0.56),
        ("56-60", 0.56, 0.60),
        ("60-65", 0.60, 0.65),
        ("65-70", 0.65, 0.70),
        ("70-75", 0.70, 0.7500000001),
    )
    return _distribution(values) | {
        "buckets": {
            label: sum(lower <= value < upper for value in values)
            for label, lower, upper in buckets
        },
        "probabilities_95_to_100": sum(value >= 0.95 for value in values),
    }


def _edge_distribution(probabilities: list[dict[str, Any]]) -> dict[str, Any]:
    edges = [item["shadow_edge"] for item in probabilities]
    return _distribution(edges) | {
        "positive_edge_count": sum(edge > 0 for edge in edges),
        "nonpositive_edge_count": sum(edge <= 0 for edge in edges),
        "price_source_counts": {PRICE_SOURCE: len(edges)},
    }


def _safety_funnel(probabilities: list[dict[str, Any]]) -> dict[str, int]:
    price_positive = [item for item in probabilities if item["shadow_edge"] > 0]
    probability_threshold = [
        item
        for item in price_positive
        if item["selected_probability"] >= item["break_even_probability"] + 0.02
    ]
    evidence = [
        item
        for item in probability_threshold
        if item["row"].minimum_games_used >= 4
    ]
    spread_safe = [
        item
        for item in evidence
        if (
            abs(item["row"].market_margin) <= 21.0
            and item["selected_probability"]
            >= item["break_even_probability"] + 0.02
        )
        or (
            21.0 < abs(item["row"].market_margin) <= 30.0
            and item["selected_probability"]
            >= item["break_even_probability"] + 0.04
        )
    ]
    return {
        "eligible": len(probabilities),
        "price_positive": len(price_positive),
        "probability_threshold": len(probability_threshold),
        "evidence_at_least_4": len(evidence),
        "spread_safety": len(spread_safe),
    }


def _bucket_counts(
    rows: list[ShadowRow],
    definitions: tuple[tuple[str, float, float], ...],
    value_getter: Any,
) -> dict[str, Any]:
    denominator = len(rows)
    return {
        label: {
            "n": sum(lower <= value_getter(row) < upper for row in rows),
            "percentage": (
                sum(lower <= value_getter(row) < upper for row in rows)
                / denominator
                * 100.0
                if denominator
                else 0.0
            ),
        }
        for label, lower, upper in definitions
    }


def _mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _median(values: list[float]) -> float | None:
    return float(np.median(values)) if values else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)