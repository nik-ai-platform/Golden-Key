from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable

from app.services.team_scoring_forecast import (
    CoverProbabilities,
    estimate_cover_probabilities,
)


@dataclass(frozen=True)
class ScoringForecastCase:
    game_id: int
    sport: str
    model_version: str
    kickoff_sort: float
    published_sort: float
    actual_home_margin: float
    spread_home: float
    spread_away: float | None
    selection: str
    spread_home_price: int | None
    spread_away_price: int | None
    published_selection_price: int | None
    candidate_home_margin: float | None
    incumbent_home_margin: float | None
    calibration_errors: tuple[float, ...] = ()
    incumbent_calibration_errors: tuple[float, ...] = ()


def devigged_home_probability(
    spread_home: float,
    spread_away: float | None,
    spread_home_price: int | None,
    spread_away_price: int | None,
) -> float | None:
    if (
        spread_away is None
        or spread_home_price is None
        or spread_away_price is None
        or not math.isclose(spread_home, -spread_away, abs_tol=1e-6)
    ):
        return None
    home = _implied_probability(spread_home_price)
    away = _implied_probability(spread_away_price)
    total = home + away
    return home / total if total > 0 else None


def select_positive_ev_side(
    probabilities: CoverProbabilities | None,
    home_price: int | None,
    away_price: int | None,
) -> tuple[str, float] | None:
    if probabilities is None or home_price is None or away_price is None:
        return None
    home_value = (
        probabilities.home_cover * _unit_win_profit(home_price)
        - probabilities.away_cover
    )
    away_value = (
        probabilities.away_cover * _unit_win_profit(away_price)
        - probabilities.home_cover
    )
    if max(home_value, away_value) <= 0:
        return None
    return ("HOME", home_value) if home_value >= away_value else ("AWAY", away_value)


def settled_unit_profit(
    *,
    selected_side: str,
    outcome: str,
    american_price: int | None,
) -> float | None:
    if american_price is None:
        return None
    if outcome == "PUSH":
        return 0.0
    if outcome == "PASS":
        return None
    if outcome == "WIN":
        return _unit_win_profit(american_price)
    if outcome == "LOSS":
        return -1.0
    raise ValueError(f"unsupported outcome {outcome!r} for {selected_side}")


def cover_outcome(
    actual_home_margin: float,
    spread_home: float,
    side: str,
) -> str:
    home_line_margin = actual_home_margin + spread_home
    if math.isclose(home_line_margin, 0.0, abs_tol=1e-9):
        return "PUSH"
    home_covered = home_line_margin > 0
    if side == "HOME":
        return "WIN" if home_covered else "LOSS"
    if side == "AWAY":
        return "LOSS" if home_covered else "WIN"
    raise ValueError("side must be HOME or AWAY")


def probability_metrics(
    cases: Iterable[tuple[float, str]],
    *,
    bootstrap_samples: int = 500,
    seed: int = 20261009,
) -> dict:
    rows = tuple((p, y) for p, y in cases if y in {"WIN", "LOSS"})
    if not rows:
        return {
            "sample_size": 0,
            "brier": None,
            "brier_ci95": None,
            "log_loss": None,
            "log_loss_ci95": None,
            "calibration": [],
        }

    def score(sample: tuple[tuple[float, str], ...]) -> tuple[float, float]:
        briers = []
        losses = []
        for probability, outcome in sample:
            p = min(1.0 - 1e-12, max(1e-12, probability))
            actual = 1.0 if outcome == "WIN" else 0.0
            briers.append((p - actual) ** 2)
            losses.append(-(actual * math.log(p) + (1.0 - actual) * math.log(1.0 - p)))
        return sum(briers) / len(briers), sum(losses) / len(losses)

    brier, logloss = score(rows)
    rng = random.Random(seed)
    boot_brier: list[float] = []
    boot_logloss: list[float] = []
    for _ in range(bootstrap_samples):
        sample = tuple(rows[rng.randrange(len(rows))] for _ in rows)
        brier_value, loss_value = score(sample)
        boot_brier.append(brier_value)
        boot_logloss.append(loss_value)

    return {
        "sample_size": len(rows),
        "brier": round(brier, 6),
        "brier_ci95": _percentile_interval(boot_brier),
        "log_loss": round(logloss, 6),
        "log_loss_ci95": _percentile_interval(boot_logloss),
        "calibration": _calibration(rows),
    }


def evaluate_forecasts(
    cases: Iterable[ScoringForecastCase],
    *,
    minimum_calibration_errors: int = 30,
) -> dict:
    rows = tuple(cases)
    candidate_errors = tuple(
        item.actual_home_margin - item.candidate_home_margin
        for item in rows
        if item.candidate_home_margin is not None
    )
    metrics: dict[str, list] = {
        "candidate_margin_errors": [],
        "market_margin_errors": [],
        "incumbent_margin_errors": [],
        "candidate_home_probability": [],
        "market_home_probability": [],
        "incumbent_home_probability": [],
        "candidate_roi": [],
        "incumbent_margin_roi": [],
        "published_npi_pick_roi": [],
    }
    candidate_pick_returns: dict[tuple[str, str], list[float]] = {}
    incumbent_margin_pick_returns: dict[tuple[str, str], list[float]] = {}
    published_pick_returns: dict[tuple[str, str], list[float]] = {}
    coverage = {
        "cases": len(rows),
        "candidate_margin_available": 0,
        "candidate_probability_available": 0,
        "candidate_actionable_picks": 0,
        "incumbent_margin_available": 0,
        "paired_market_prices": 0,
        "candidate_actual_prices_available": 0,
        "incumbent_actual_prices_available": 0,
        "published_npi_pick_price_missing": 0,
        "candidate_pushes": 0,
        "incumbent_pushes": 0,
        "candidate_probability_unavailable": 0,
        "candidate_no_paired_prices": 0,
        "candidate_no_positive_expected_value": 0,
    }

    for item in rows:
        metrics["market_margin_errors"].append(
            (-item.spread_home) - item.actual_home_margin
        )
        if item.candidate_home_margin is not None:
            coverage["candidate_margin_available"] += 1
            metrics["candidate_margin_errors"].append(
                item.candidate_home_margin - item.actual_home_margin
            )
        if item.incumbent_home_margin is not None:
            coverage["incumbent_margin_available"] += 1
            metrics["incumbent_margin_errors"].append(
                item.incumbent_home_margin - item.actual_home_margin
            )

        market_probability = devigged_home_probability(
            item.spread_home,
            item.spread_away,
            item.spread_home_price,
            item.spread_away_price,
        )
        if market_probability is not None:
            coverage["paired_market_prices"] += 1
            market_outcome = cover_outcome(
                item.actual_home_margin, item.spread_home, "HOME"
            )
            metrics["market_home_probability"].append(
                (market_probability, market_outcome)
            )

        candidate_probability = estimate_cover_probabilities(
            forecast_home_margin=item.candidate_home_margin,
            spread_home=item.spread_home,
            earlier_forecast_errors=item.calibration_errors,
            minimum_errors=minimum_calibration_errors,
        ) if item.candidate_home_margin is not None else None
        incumbent_probability = estimate_cover_probabilities(
            forecast_home_margin=item.incumbent_home_margin,
            spread_home=item.spread_home,
            earlier_forecast_errors=item.incumbent_calibration_errors,
            minimum_errors=minimum_calibration_errors,
        ) if item.incumbent_home_margin is not None else None

        if item.candidate_home_margin is not None and candidate_probability is None:
            coverage["candidate_probability_unavailable"] += 1
        if candidate_probability is not None and (
            item.spread_home_price is None or item.spread_away_price is None
        ):
            coverage["candidate_no_paired_prices"] += 1

        for name, probability in (
            ("candidate", candidate_probability),
            ("incumbent", incumbent_probability),
        ):
            if probability is None:
                continue
            if name == "candidate":
                coverage["candidate_probability_available"] += 1
                home_price, away_price = item.spread_home_price, item.spread_away_price
            else:
                home_price, away_price = item.spread_home_price, item.spread_away_price
            outcome = cover_outcome(item.actual_home_margin, item.spread_home, "HOME")
            metrics[f"{name}_home_probability"].append(
                (probability.home_cover, outcome)
            )
            pick = select_positive_ev_side(probability, home_price, away_price)
            if pick is None:
                if name == "candidate":
                    coverage["candidate_no_positive_expected_value"] += 1
                continue
            side = pick[0]
            coverage[f"{name}_actionable_picks"] = (
                coverage.get(f"{name}_actionable_picks", 0) + 1
            )
            price = home_price if side == "HOME" else away_price
            pick_outcome = cover_outcome(
                item.actual_home_margin, item.spread_home, side
            )
            profit = settled_unit_profit(
                selected_side=side,
                outcome=pick_outcome,
                american_price=price,
            )
            if profit is not None:
                metric_name = (
                    "candidate_roi" if name == "candidate" else "incumbent_margin_roi"
                )
                metrics[metric_name].append(profit)
                side_type = _side_type(side, item.spread_home)
                band = _spread_band(item.spread_home)
                destination = (
                    candidate_pick_returns
                    if name == "candidate"
                    else incumbent_margin_pick_returns
                )
                destination.setdefault((side_type, band), []).append(profit)
                coverage[f"{name}_actual_prices_available"] += 1
                if pick_outcome == "PUSH":
                    coverage[f"{name}_pushes"] += 1

        if item.selection in {"HOME", "AWAY"}:
            price = item.published_selection_price
            pick_outcome = cover_outcome(
                item.actual_home_margin,
                item.spread_home,
                item.selection,
            )
            profit = settled_unit_profit(
                selected_side=item.selection,
                outcome=pick_outcome,
                american_price=price,
            )
            if profit is not None:
                metrics["published_npi_pick_roi"].append(profit)
                published_pick_returns.setdefault(
                    (_side_type(item.selection, item.spread_home), _spread_band(item.spread_home)),
                    [],
                ).append(profit)
                coverage["incumbent_actual_prices_available"] += 1
                if pick_outcome == "PUSH":
                    coverage["incumbent_pushes"] += 1
            else:
                coverage["published_npi_pick_price_missing"] += 1

    return {
        "coverage": coverage,
        "candidate_margin": margin_metrics(metrics["candidate_margin_errors"]),
        "incumbent_npi_margin": margin_metrics(metrics["incumbent_margin_errors"]),
        "frozen_market_spread_margin": margin_metrics(metrics["market_margin_errors"]),
        "candidate_cover_probability": probability_metrics(
            metrics["candidate_home_probability"]
        ),
        "incumbent_cover_probability": probability_metrics(
            metrics["incumbent_home_probability"]
        ),
        "devigged_market_cover_probability": probability_metrics(
            metrics["market_home_probability"]
        ),
        "candidate_actual_price_roi": roi_metrics(metrics["candidate_roi"]),
        "incumbent_margin_actual_price_roi": roi_metrics(
            metrics["incumbent_margin_roi"]
        ),
        "published_npi_pick_actual_price_roi": roi_metrics(
            metrics["published_npi_pick_roi"]
        ),
        "candidate_pick_roi_by_favorite_status_and_spread_band": [
            {
                "side_type": side_type,
                "spread_band": spread_band,
                **roi_metrics(profits),
            }
            for (side_type, spread_band), profits in sorted(candidate_pick_returns.items())
        ],
        "incumbent_margin_pick_roi_by_favorite_status_and_spread_band": [
            {
                "side_type": side_type,
                "spread_band": spread_band,
                **roi_metrics(profits),
            }
            for (side_type, spread_band), profits in sorted(incumbent_margin_pick_returns.items())
        ],
        "published_pick_roi_by_favorite_status_and_spread_band": [
            {
                "side_type": side_type,
                "spread_band": spread_band,
                **roi_metrics(profits),
            }
            for (side_type, spread_band), profits in sorted(published_pick_returns.items())
        ],
    }


def margin_metrics(errors: Iterable[float]) -> dict:
    values = tuple(float(error) for error in errors)
    if not values:
        return {
            "sample_size": 0,
            "mae": None,
            "mae_ci95": None,
            "rmse": None,
            "rmse_ci95": None,
        }
    mae = sum(abs(error) for error in values) / len(values)
    rmse = math.sqrt(sum(error * error for error in values) / len(values))
    rng = random.Random(20261009)
    mae_samples = []
    rmse_samples = []
    for _ in range(500):
        sample = [values[rng.randrange(len(values))] for _ in values]
        mae_samples.append(sum(abs(value) for value in sample) / len(sample))
        rmse_samples.append(math.sqrt(sum(value * value for value in sample) / len(sample)))
    return {
        "sample_size": len(values),
        "mae": round(mae, 4),
        "mae_ci95": _percentile_interval(mae_samples),
        "rmse": round(rmse, 4),
        "rmse_ci95": _percentile_interval(rmse_samples),
    }


def roi_metrics(profits: Iterable[float]) -> dict:
    values = tuple(profits)
    if not values:
        return {
            "sample_size": 0,
            "unit_roi_percent": None,
            "unit_roi_ci95": None,
            "units_profit": 0.0,
        }
    roi = sum(values) / len(values) * 100
    rng = random.Random(20261009)
    boot = [
        sum(values[rng.randrange(len(values))] for _ in values) / len(values) * 100
        for _ in range(500)
    ]
    return {
        "sample_size": len(values),
        "unit_roi_percent": round(roi, 4),
        "unit_roi_ci95": _percentile_interval(boot),
        "units_profit": round(sum(values), 4),
    }


def _calibration(rows: tuple[tuple[float, str], ...]) -> list[dict]:
    bins: list[list[tuple[float, str]]] = [[] for _ in range(10)]
    for probability, outcome in rows:
        bins[min(9, max(0, int(probability * 10)))].append((probability, outcome))
    result = []
    for index, bucket in enumerate(bins):
        if not bucket:
            continue
        wins = sum(outcome == "WIN" for _, outcome in bucket)
        result.append(
            {
                "range": f"{index / 10:.1f}-{(index + 1) / 10:.1f}",
                "sample_size": len(bucket),
                "mean_predicted": round(
                    sum(probability for probability, _ in bucket) / len(bucket), 4
                ),
                "observed_cover_rate": round(wins / len(bucket), 4),
                "observed_cover_ci95": _wilson_interval(wins, len(bucket)),
            }
        )
    return result


def _wilson_interval(successes: int, count: int) -> list[float]:
    if count == 0:
        return []
    z = 1.959963984540054
    p = successes / count
    divisor = 1 + z * z / count
    center = (p + z * z / (2 * count)) / divisor
    radius = (
        z
        * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count))
        / divisor
    )
    return [round(max(0.0, center - radius), 4), round(min(1.0, center + radius), 4)]


def _percentile_interval(values: Iterable[float]) -> list[float] | None:
    ordered = sorted(values)
    if not ordered:
        return None
    return [
        round(ordered[int((len(ordered) - 1) * 0.025)], 4),
        round(ordered[int((len(ordered) - 1) * 0.975)], 4),
    ]


def _implied_probability(price: int) -> float:
    value = float(price)
    if value == 0:
        raise ValueError("American odds cannot be zero")
    if value < 0:
        return abs(value) / (abs(value) + 100)
    return 100 / (value + 100)


def _unit_win_profit(price: int) -> float:
    if price == 0:
        raise ValueError("American odds cannot be zero")
    return price / 100 if price > 0 else 100 / abs(price)


def _side_type(side: str, spread_home: float) -> str:
    favorite_side = "HOME" if spread_home < 0 else "AWAY"
    return "FAVORITE" if side == favorite_side else "UNDERDOG"


def _spread_band(spread_home: float) -> str:
    line = abs(spread_home)
    if line < 3.5:
        return "0-3"
    if line <= 7:
        return "3.5-7"
    if line <= 14:
        return "7.5-14"
    return "above-14"
