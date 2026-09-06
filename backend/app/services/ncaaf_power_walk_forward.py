from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from statistics import median

import numpy as np
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.odds import Odds
from app.services.ncaaf_power_rating_service import (
    PROVISIONAL_HOME_FIELD_POINTS,
    calculate_team_ratings,
    get_expected_home_margin,
)


BOTH_RATED = "BOTH_RATED"
HOME_UNRATED = "HOME_UNRATED"
AWAY_UNRATED = "AWAY_UNRATED"
BOTH_UNRATED = "BOTH_UNRATED"


@dataclass(frozen=True)
class WalkForwardPrediction:
    game_id: int
    kickoff: datetime
    week_bucket: str
    home_team_id: int
    away_team_id: int
    neutral_site: bool
    classification: str
    home_rating: float | None
    away_rating: float | None
    home_uncertainty: float | None
    away_uncertainty: float | None
    home_games_used: int | None
    away_games_used: int | None
    predicted_home_margin: float | None
    actual_home_margin: float
    prediction_error: float | None
    market_expected_home_margin: float | None

    @property
    def combined_uncertainty(self) -> float | None:
        if self.home_uncertainty is None or self.away_uncertainty is None:
            return None
        return math.hypot(self.home_uncertainty, self.away_uncertainty)

    @property
    def min_prior_games(self) -> int | None:
        if self.home_games_used is None or self.away_games_used is None:
            return None
        return min(self.home_games_used, self.away_games_used)


def generate_walk_forward_predictions(
    db: Session,
    season: int,
) -> tuple[WalkForwardPrediction, ...]:
    target_games = (
        db.query(Game)
        .filter(
            Game.sport == "NCAAF",
            Game.season == season,
            Game.status == "final",
            Game.home_score.isnot(None),
            Game.away_score.isnot(None),
            Game.neutral_site.isnot(None),
        )
        .order_by(Game.game_date, Game.id)
        .all()
    )
    market_margins = _pregame_market_margins(db, season)
    ratings_by_kickoff = {}
    predictions = []

    for game in target_games:
        kickoff = _database_timestamp_as_utc(game.game_date)
        if kickoff not in ratings_by_kickoff:
            ratings_by_kickoff[kickoff] = calculate_team_ratings(
                db, kickoff, season=season, prior_ratings=None
            )
        ratings = ratings_by_kickoff[kickoff]
        home = ratings.get(game.home_team_id)
        away = ratings.get(game.away_team_id)
        classification = _classification(home is not None, away is not None)
        predicted_margin = None
        error = None
        if home is not None and away is not None:
            predicted_margin = get_expected_home_margin(home, away, game.neutral_site)
            error = float(game.home_score) - float(game.away_score) - predicted_margin

        predictions.append(
            WalkForwardPrediction(
                game_id=game.id,
                kickoff=kickoff,
                week_bucket=_week_bucket(kickoff),
                home_team_id=game.home_team_id,
                away_team_id=game.away_team_id,
                neutral_site=game.neutral_site,
                classification=classification,
                home_rating=home.rating if home else None,
                away_rating=away.rating if away else None,
                home_uncertainty=home.uncertainty if home else None,
                away_uncertainty=away.uncertainty if away else None,
                home_games_used=home.games_used if home else None,
                away_games_used=away.games_used if away else None,
                predicted_home_margin=predicted_margin,
                actual_home_margin=float(game.home_score) - float(game.away_score),
                prediction_error=error,
                market_expected_home_margin=market_margins.get(game.id),
            )
        )
    return tuple(predictions)


def build_walk_forward_report(
    db: Session,
    season: int,
) -> dict:
    predictions = generate_walk_forward_predictions(db, season)
    both_rated = [row for row in predictions if row.classification == BOTH_RATED]
    total = len(predictions)
    coverage = {
        label: sum(row.classification == label for row in predictions)
        for label in (BOTH_RATED, HOME_UNRATED, AWAY_UNRATED, BOTH_UNRATED)
    }
    errors = np.array([row.prediction_error for row in both_rated], dtype=float)
    absolute_errors = np.abs(errors)
    error_percentiles = {
        str(percentile): float(np.percentile(errors, percentile))
        for percentile in (5, 10, 25, 50, 75, 90, 95)
    } if len(errors) else {}

    minimum_evidence = {
        str(threshold): _metrics(
            [row for row in both_rated if (row.min_prior_games or 0) >= threshold], total
        )
        for threshold in range(1, 7)
    }
    ranked_uncertainty = sorted(
        both_rated,
        key=lambda row: (row.combined_uncertainty, row.game_id),
    )
    uncertainty_quartiles = {
        f"Q{index + 1}": _metrics(list(rows), total)
        for index, rows in enumerate(np.array_split(ranked_uncertainty, 4))
    }
    weeks = {}
    for bucket in sorted({row.week_bucket for row in predictions}):
        bucket_rows = [row for row in predictions if row.week_bucket == bucket]
        bucket_rated = [row for row in bucket_rows if row.classification == BOTH_RATED]
        weeks[bucket] = {
            "games": len(bucket_rows),
            **_metrics(bucket_rated, len(bucket_rows)),
        }

    neutral = [row for row in both_rated if row.neutral_site]
    non_neutral = [row for row in both_rated if not row.neutral_site]
    home_field_residuals = np.array(
        [
            row.actual_home_margin - (row.home_rating - row.away_rating)
            for row in non_neutral
        ],
        dtype=float,
    )
    naive_errors = np.array(
        [
            row.actual_home_margin
            - (0.0 if row.neutral_site else PROVISIONAL_HOME_FIELD_POINTS)
            for row in both_rated
        ],
        dtype=float,
    )
    naive_predictions = np.array(
        [0.0 if row.neutral_site else PROVISIONAL_HOME_FIELD_POINTS for row in both_rated],
        dtype=float,
    )
    primary = _metrics(both_rated, total)
    naive = _metrics_from_errors(
        naive_errors,
        both_rated,
        total,
        predicted_values=naive_predictions,
    )
    market_rows = [row for row in both_rated if row.market_expected_home_margin is not None]
    market_errors = np.array(
        [row.actual_home_margin - row.market_expected_home_margin for row in market_rows],
        dtype=float,
    )

    return {
        "season": season,
        "coverage": {"total_games": total, **coverage},
        "primary": {
            **primary,
            "median_absolute_error": float(np.median(absolute_errors)) if len(errors) else None,
            "residual_standard_deviation": float(np.std(errors, ddof=1)) if len(errors) > 1 else None,
            "robust_mad_dispersion": _mad_dispersion(errors),
            "error_percentiles": error_percentiles,
        },
        "minimum_evidence": minimum_evidence,
        "uncertainty_quartiles": uncertainty_quartiles,
        "chronological_weeks": weeks,
        "home_field": {
            "neutral": _metrics(neutral, total),
            "non_neutral": _metrics(non_neutral, total),
            "non_neutral_raw_residual_mean": float(np.mean(home_field_residuals)) if len(home_field_residuals) else None,
            "non_neutral_raw_residual_median": float(np.median(home_field_residuals)) if len(home_field_residuals) else None,
        },
        "largest_errors": [
            {**asdict(row), "combined_uncertainty": row.combined_uncertainty}
            for row in sorted(
                both_rated,
                key=lambda row: (-abs(row.prediction_error), row.game_id),
            )[:25]
        ],
        "naive_baseline": {
            "model": primary,
            "naive_hfa": naive,
            "mae_improvement_percent": _improvement(naive["mae"], primary["mae"]),
            "rmse_improvement_percent": _improvement(naive["rmse"], primary["rmse"]),
        },
        "market_benchmark": {
            "n": len(market_rows),
            "model": _metrics(market_rows, len(market_rows)),
            "market": _metrics_from_errors(market_errors, market_rows, len(market_rows), market=True),
        },
        "market_disagreement": _market_disagreement(market_rows),
        "spread_magnitude": _spread_magnitude(market_rows),
        "favorite_direction": _favorite_direction(market_rows),
    }


def _metrics(rows: list[WalkForwardPrediction], denominator: int) -> dict:
    errors = np.array([row.prediction_error for row in rows], dtype=float)
    return _metrics_from_errors(errors, rows, denominator)


def _metrics_from_errors(
    errors: np.ndarray,
    rows: list[WalkForwardPrediction],
    denominator: int,
    *,
    market: bool = False,
    predicted_values: np.ndarray | None = None,
) -> dict:
    if not len(errors):
        return {"n": 0, "coverage": 0.0, "mae": None, "rmse": None, "mean_error": None, "correlation": None}
    predictions = predicted_values
    if predictions is None:
        predictions = np.array(
            [
                row.market_expected_home_margin if market else row.predicted_home_margin
                for row in rows
            ],
            dtype=float,
        )
    actuals = np.array([row.actual_home_margin for row in rows], dtype=float)
    correlation = None
    if len(rows) > 1 and np.std(predictions) > 0 and np.std(actuals) > 0:
        correlation = float(np.corrcoef(predictions, actuals)[0, 1])
    return {
        "n": len(rows),
        "coverage": len(rows) / denominator if denominator else 0.0,
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "mean_error": float(np.mean(errors)),
        "correlation": correlation,
    }


def _pregame_market_margins(db: Session, season: int) -> dict[int, float]:
    rows = (
        db.query(Odds, Game.game_date)
        .join(Game, Game.id == Odds.game_id)
        .filter(
            Game.sport == "NCAAF",
            Game.season == season,
            Odds.spread_home.isnot(None),
            Odds.created_at <= Game.game_date,
        )
        .order_by(Odds.game_id, Odds.created_at.desc(), Odds.id.desc())
        .all()
    )
    margins = {}
    for odds, _ in rows:
        margins.setdefault(odds.game_id, -float(odds.spread_home))
    return margins


def _market_disagreement(rows: list[WalkForwardPrediction]) -> dict:
    if not rows:
        return {"summary": {}, "buckets": {}}
    disagreements = np.array(
        [row.predicted_home_margin - row.market_expected_home_margin for row in rows], dtype=float
    )
    buckets = {
        "0-3": (0, 3),
        "3-7": (3, 7),
        "7-14": (7, 14),
        "14-21": (14, 21),
        "21+": (21, math.inf),
    }
    return {
        "summary": {
            "mean": float(np.mean(disagreements)),
            "median": float(np.median(disagreements)),
            "standard_deviation": float(np.std(disagreements, ddof=1)) if len(rows) > 1 else 0.0,
            "robust_mad_dispersion": _mad_dispersion(disagreements),
        },
        "buckets": {
            label: _comparison_metrics(
                [row for row, value in zip(rows, np.abs(disagreements), strict=True) if lower <= value < upper]
            )
            for label, (lower, upper) in buckets.items()
        },
    }


def _spread_magnitude(rows: list[WalkForwardPrediction]) -> dict:
    buckets = {
        "0-3": (0, 3),
        "3.5-7": (3, 7),
        "7.5-10": (7, 10),
        "10.5-14": (10, 14),
        "14.5-21": (14, 21),
        "21.5-30": (21, 30),
        "30.5+": (30, math.inf),
    }
    return {
        label: _comparison_metrics(
            [
                row
                for row in rows
                if (lower == 0 and abs(row.market_expected_home_margin) <= upper)
                or lower < abs(row.market_expected_home_margin) <= upper
            ]
        )
        for label, (lower, upper) in buckets.items()
    }


def _favorite_direction(rows: list[WalkForwardPrediction]) -> dict:
    return {
        "home_favorite": _metrics([row for row in rows if row.market_expected_home_margin > 0], len(rows)),
        "away_favorite": _metrics([row for row in rows if row.market_expected_home_margin < 0], len(rows)),
        "pick_em": _metrics([row for row in rows if row.market_expected_home_margin == 0], len(rows)),
    }


def _comparison_metrics(rows: list[WalkForwardPrediction]) -> dict:
    model = _metrics(rows, len(rows))
    market_errors = np.array(
        [row.actual_home_margin - row.market_expected_home_margin for row in rows], dtype=float
    )
    market = _metrics_from_errors(market_errors, rows, len(rows), market=True)
    return {
        "n": len(rows),
        "model_mae": model["mae"],
        "model_rmse": model["rmse"],
        "market_mae": market["mae"],
        "market_rmse": market["rmse"],
        "mean_model_error": model["mean_error"],
    }


def _classification(home_rated: bool, away_rated: bool) -> str:
    if home_rated and away_rated:
        return BOTH_RATED
    if not home_rated and not away_rated:
        return BOTH_UNRATED
    return HOME_UNRATED if not home_rated else AWAY_UNRATED


def _week_bucket(kickoff: datetime) -> str:
    return (kickoff.date() - timedelta(days=kickoff.weekday())).isoformat()


def _mad_dispersion(values: np.ndarray) -> float | None:
    if not len(values):
        return None
    center = float(np.median(values))
    return 1.4826 * float(np.median(np.abs(values - center)))


def _improvement(baseline: float | None, model: float | None) -> float | None:
    if baseline in (None, 0) or model is None:
        return None
    return 100.0 * (baseline - model) / baseline


def _database_timestamp_as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)