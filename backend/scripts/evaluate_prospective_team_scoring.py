from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.team_scoring_evaluation import (
    cover_outcome,
    devigged_home_probability,
    paired_margin_comparison,
    probability_metrics,
    roi_metrics,
    settled_unit_profit,
)
from app.services.team_scoring_forecast import MODEL_VERSION, TimestampedScore
from scripts.record_prospective_team_scoring import (
    PROSPECTIVE_PERIOD_START,
    PROTOCOL_VERSION,
    _score_observations,
)
from scripts.report_odds_capture_coverage import (
    build_report as build_collection_coverage,
)


def _json_rows(path: Path):
    record_files = [path] if path.is_file() else sorted(path.glob("attempts*"))
    for record_file in record_files:
        opener = gzip.open if record_file.suffix == ".gz" else open
        with opener(record_file, "rt", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)


def _attempt_id(record: dict) -> str:
    if record.get("run_id"):
        return f"{record['run_id']}:{record['game_id']}"
    payload = json.dumps(
        {
            key: record.get(key)
            for key in (
                "protocol_version",
                "candidate_model_version",
                "game_id",
                "prediction_timestamp",
                "candidate_home_margin",
                "frozen_odds_snapshot_id",
            )
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _attempt_projection(record: dict) -> dict:
    keys = (
        "record_type",
        "protocol_version",
        "candidate_model_version",
        "game_id",
        "sport",
        "run_id",
        "prediction_timestamp",
        "kickoff",
        "candidate_margin_available",
        "candidate_home_margin",
        "frozen_odds_snapshot_id",
        "spread_home",
        "spread_away",
        "spread_home_price",
        "spread_away_price",
        "cover_probability",
        "shadow_selection",
        "rejection_reasons",
    )
    return {key: record.get(key) for key in keys}


def _paired_probability_comparison(
    rows: list[tuple[float, float, str]],
) -> dict:
    values = [
        (candidate, market, 1.0 if outcome == "WIN" else 0.0)
        for candidate, market, outcome in rows
        if outcome in {"WIN", "LOSS"}
    ]
    if not values:
        return {
            "sample_size": 0,
            "candidate_minus_market_brier": None,
            "brier_delta_ci95": None,
            "candidate_minus_market_log_loss": None,
            "log_loss_delta_ci95": None,
            "promotion_brier_gate_passed": False,
            "promotion_log_loss_gate_passed": False,
        }

    def loss(candidate: float, market: float, actual: float) -> tuple[float, float]:
        candidate = min(1 - 1e-12, max(1e-12, candidate))
        market = min(1 - 1e-12, max(1e-12, market))
        candidate_log = -(
            actual * math.log(candidate) + (1 - actual) * math.log(1 - candidate)
        )
        market_log = -(actual * math.log(market) + (1 - actual) * math.log(1 - market))
        return (candidate - actual) ** 2 - (
            market - actual
        ) ** 2, candidate_log - market_log

    deltas = [loss(*row) for row in values]
    brier_delta = sum(row[0] for row in deltas) / len(deltas)
    log_loss_delta = sum(row[1] for row in deltas) / len(deltas)
    rng = random.Random(20261009)
    brier_bootstrap = []
    log_loss_bootstrap = []
    for _ in range(1000):
        sample = [deltas[rng.randrange(len(deltas))] for _ in deltas]
        brier_bootstrap.append(sum(row[0] for row in sample) / len(sample))
        log_loss_bootstrap.append(sum(row[1] for row in sample) / len(sample))
    brier_ci = _percentile_interval(brier_bootstrap)
    log_loss_ci = _percentile_interval(log_loss_bootstrap)
    return {
        "sample_size": len(values),
        "candidate_minus_market_brier": round(brier_delta, 6),
        "brier_delta_ci95": brier_ci,
        "candidate_minus_market_log_loss": round(log_loss_delta, 6),
        "log_loss_delta_ci95": log_loss_ci,
        "promotion_brier_gate_passed": bool(
            len(values) >= 200 and brier_ci is not None and brier_ci[1] < 0
        ),
        "promotion_log_loss_gate_passed": bool(
            len(values) >= 200 and log_loss_delta <= 0
        ),
    }


def _percentile_interval(values: list[float]) -> list[float] | None:
    ordered = sorted(values)
    if not ordered:
        return None
    return [
        round(ordered[int((len(ordered) - 1) * 0.025)], 6),
        round(ordered[int((len(ordered) - 1) * 0.975)], 6),
    ]


def _calibration_intercept_slope(
    rows: list[tuple[float, str]],
) -> dict:
    usable = [
        (min(1 - 1e-6, max(1e-6, probability)), outcome == "WIN")
        for probability, outcome in rows
        if outcome in {"WIN", "LOSS"}
    ]
    if len(usable) < 20 or len({actual for _, actual in usable}) < 2:
        return {
            "sample_size": len(usable),
            "intercept": None,
            "slope": None,
            "intercept_ci95": None,
            "slope_ci95": None,
            "unavailable_reason": "insufficient_outcome_variation_or_sample",
        }
    logits = np.array(
        [
            [1.0, math.log(probability / (1.0 - probability))]
            for probability, _ in usable
        ],
        dtype=np.float64,
    )
    actual = np.array([float(value) for _, value in usable], dtype=np.float64)
    coefficients = np.array([0.0, 1.0], dtype=np.float64)
    try:
        for _ in range(100):
            linear = np.clip(logits @ coefficients, -30, 30)
            fitted = 1.0 / (1.0 + np.exp(-linear))
            weights = np.maximum(fitted * (1.0 - fitted), 1e-12)
            information = logits.T @ (weights[:, None] * logits)
            step = np.linalg.solve(
                information + np.eye(2, dtype=np.float64) * 1e-12,
                logits.T @ (actual - fitted),
            )
            coefficients += step
            if float(np.max(np.abs(step))) < 1e-8:
                break
        covariance = np.linalg.inv(information)
    except np.linalg.LinAlgError:
        return {
            "sample_size": len(usable),
            "intercept": None,
            "slope": None,
            "intercept_ci95": None,
            "slope_ci95": None,
            "unavailable_reason": "singular_calibration_fit",
        }
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    return {
        "sample_size": len(usable),
        "intercept": round(float(coefficients[0]), 6),
        "slope": round(float(coefficients[1]), 6),
        "intercept_ci95": [
            round(float(coefficients[0] - 1.96 * standard_errors[0]), 6),
            round(float(coefficients[0] + 1.96 * standard_errors[0]), 6),
        ],
        "slope_ci95": [
            round(float(coefficients[1] - 1.96 * standard_errors[1]), 6),
            round(float(coefficients[1] + 1.96 * standard_errors[1]), 6),
        ],
    }


def _primary_attempts(records: Iterable[dict]) -> dict[int, dict]:
    primary: dict[int, dict] = {}
    for record in records:
        if (
            record.get("record_type") != "candidate_forecast_attempt"
            or record.get("protocol_version") != PROTOCOL_VERSION
            or record.get("candidate_model_version") != MODEL_VERSION
            or not record.get("candidate_margin_available")
            or record.get("candidate_home_margin") is None
            or not _attempt_receipt_provenance_is_valid(record)
        ):
            continue
        kickoff = datetime.fromisoformat(record["kickoff"])
        predicted_at = datetime.fromisoformat(record["prediction_timestamp"])
        if kickoff <= predicted_at or predicted_at < PROSPECTIVE_PERIOD_START:
            continue
        game_id = int(record["game_id"])
        projected = _attempt_projection(record)
        current = primary.get(game_id)
        if current is None or (
            datetime.fromisoformat(projected["prediction_timestamp"]),
            _attempt_id(record),
        ) < (
            datetime.fromisoformat(current["prediction_timestamp"]),
            _attempt_id(current),
        ):
            primary[game_id] = projected
    return primary


def _attempt_receipt_provenance_is_valid(record: dict) -> bool:
    inputs = record.get("history_observation_inputs")
    if not isinstance(inputs, list):
        return False
    if any(not isinstance(item, dict) for item in inputs):
        return False
    return all(
        str(item.get("source_provider") or "").lower() != "cfbd"
        or item.get("receipt_basis") == "shadow_import_receipt"
        for item in inputs
    )


def _valid_final_score(item: TimestampedScore) -> bool:
    return (
        item.status.strip().lower() in {"final", "completed"}
        and item.home_score is not None
        and item.away_score is not None
        and math.isfinite(float(item.home_score))
        and math.isfinite(float(item.away_score))
        and float(item.home_score) >= 0
        and float(item.away_score) >= 0
    )


def _load_settlement_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def build_settlement_events(
    attempts: Iterable[dict],
    observations: list[TimestampedScore],
    *,
    as_of: datetime,
    existing_events: list[dict],
) -> tuple[list[dict], dict[int, dict]]:
    cutoff = as_of.astimezone(UTC) if as_of.tzinfo else as_of.replace(tzinfo=UTC)
    primary = _primary_attempts(attempts)
    known_event_keys = {
        row["evaluation_key"] for row in existing_events if row.get("evaluation_key")
    }
    latest_by_game: dict[int, dict] = {}
    for row in existing_events:
        current = latest_by_game.get(int(row["game_id"]))
        if current is None or (
            row["score_observed_at"],
            int(row["score_observation_id"]),
        ) > (
            current["score_observed_at"],
            int(current["score_observation_id"]),
        ):
            latest_by_game[int(row["game_id"])] = row

    scores_by_game: dict[int, list[TimestampedScore]] = defaultdict(list)
    for score in observations:
        scores_by_game[score.game_id].append(score)

    additions = []
    for game_id, attempt in sorted(primary.items()):
        attempt_at = datetime.fromisoformat(attempt["prediction_timestamp"])
        kickoff = datetime.fromisoformat(attempt["kickoff"])
        spread_home = attempt.get("spread_home")
        if spread_home is None or not math.isfinite(float(spread_home)):
            continue
        eligible = [
            score
            for score in scores_by_game.get(game_id, [])
            if _valid_final_score(score)
            and score.observed_at < cutoff
            and score.observed_at > attempt_at
            and score.observed_at >= kickoff
        ]
        if not eligible:
            continue
        score = max(eligible, key=lambda row: (row.observed_at, row.observation_id))
        evaluation_key = (
            f"{PROTOCOL_VERSION}:{MODEL_VERSION}:{game_id}:{score.observation_id}"
        )
        if evaluation_key in known_event_keys:
            continue
        actual_margin = float(score.home_score) - float(score.away_score)
        home_outcome = cover_outcome(
            actual_home_margin=actual_margin,
            spread_home=float(spread_home),
            side="HOME",
        )
        selection = attempt.get("shadow_selection")
        selected_side = selection.get("side") if isinstance(selection, dict) else None
        selected_outcome = (
            cover_outcome(
                actual_home_margin=actual_margin,
                spread_home=float(spread_home),
                side=selected_side,
            )
            if selected_side in {"HOME", "AWAY"}
            else "NO_BET"
        )
        selected_price = (
            attempt.get("spread_home_price")
            if selected_side == "HOME"
            else attempt.get("spread_away_price")
            if selected_side == "AWAY"
            else None
        )
        profit = (
            settled_unit_profit(
                selected_side=selected_side,
                outcome=selected_outcome,
                american_price=selected_price,
            )
            if selected_side in {"HOME", "AWAY"}
            else None
        )
        previous = latest_by_game.get(game_id)
        row = {
            "record_type": "prospective_settlement_evidence",
            "protocol_version": PROTOCOL_VERSION,
            "candidate_model_version": MODEL_VERSION,
            "evaluation_key": evaluation_key,
            "game_id": game_id,
            "sport": attempt["sport"],
            "primary_attempt_id": _attempt_id(attempt),
            "prediction_timestamp": attempt["prediction_timestamp"],
            "kickoff": attempt["kickoff"],
            "score_provider": score.source_provider,
            "score_source_game_id": score.source_game_id,
            "score_observation_id": score.observation_id,
            "score_observed_at": score.observed_at.isoformat(),
            "score_source_updated_at": (
                score.source_updated_at.isoformat() if score.source_updated_at else None
            ),
            "score_receipt_basis": score.receipt_basis,
            "home_score": float(score.home_score),
            "away_score": float(score.away_score),
            "actual_home_margin": actual_margin,
            "frozen_spread_home": float(spread_home),
            "frozen_spread_away": attempt.get("spread_away"),
            "spread_home_price": attempt.get("spread_home_price"),
            "spread_away_price": attempt.get("spread_away_price"),
            "home_cover_outcome": home_outcome,
            "away_cover_outcome": cover_outcome(
                actual_home_margin=actual_margin,
                spread_home=float(spread_home),
                side="AWAY",
            ),
            "candidate_home_margin": float(attempt["candidate_home_margin"]),
            "candidate_probability": attempt.get("cover_probability"),
            "selected_side": selected_side,
            "selected_outcome": selected_outcome,
            "selected_price": selected_price,
            "actual_price_unit_profit": profit,
            "supersedes_score_observation_id": (
                previous["score_observation_id"] if previous else None
            ),
            "is_score_correction": previous is not None,
            "customer_recommendation": False,
        }
        additions.append(row)
        known_event_keys.add(evaluation_key)
        latest_by_game[game_id] = row
    return additions, latest_by_game


def _append_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    os.chmod(path.parent, 0o700)
    os.chmod(path, 0o600)
    if not records:
        return
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in records
    ).encode("utf-8")
    descriptor = os.open(path, os.O_APPEND | os.O_WRONLY)
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("Could not append all prospective evaluation records")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _headline_events(events: list[dict]) -> dict[int, dict]:
    latest = {}
    for row in events:
        game_id = int(row["game_id"])
        current = latest.get(game_id)
        if current is None or (
            row["score_observed_at"],
            int(row["score_observation_id"]),
        ) > (
            current["score_observed_at"],
            int(current["score_observation_id"]),
        ):
            latest[game_id] = row
    return latest


def build_evaluation_metrics(events: list[dict]) -> dict:
    by_sport: dict[str, list[dict]] = defaultdict(list)
    for row in _headline_events(events).values():
        by_sport[row["sport"]].append(row)
    report = {}
    for sport, rows in sorted(by_sport.items()):
        margin_pairs = []
        candidate_home_probabilities = []
        market_home_probabilities = []
        paired_probability_rows = []
        profits = []
        calibration_history_counts = []
        outcome_counts = Counter()
        for row in rows:
            actual_margin = float(row["actual_home_margin"])
            spread_home = float(row["frozen_spread_home"])
            candidate_error = float(row["candidate_home_margin"]) - actual_margin
            market_error = -spread_home - actual_margin
            margin_pairs.append((candidate_error, market_error))
            outcome_counts[row["home_cover_outcome"]] += 1
            probability = row.get("candidate_probability")
            if isinstance(probability, dict):
                calibration_history_counts.append(
                    int(probability.get("calibration_games", 0))
                )
                if row["home_cover_outcome"] != "PUSH":
                    candidate_home_probabilities.append(
                        (
                            float(probability["home_cover"]),
                            row["home_cover_outcome"],
                        )
                    )
                market_probability = devigged_home_probability(
                    spread_home,
                    row.get("frozen_spread_away"),
                    row.get("spread_home_price"),
                    row.get("spread_away_price"),
                )
                if (
                    market_probability is not None
                    and row["home_cover_outcome"] != "PUSH"
                ):
                    market_home_probabilities.append(
                        (market_probability, row["home_cover_outcome"])
                    )
                    paired_probability_rows.append(
                        (
                            float(probability["home_cover"]),
                            market_probability,
                            row["home_cover_outcome"],
                        )
                    )
            if row.get("actual_price_unit_profit") is not None:
                profits.append(float(row["actual_price_unit_profit"]))
        margin_comparison = paired_margin_comparison(margin_pairs)
        paired_probability_comparison = _paired_probability_comparison(
            paired_probability_rows
        )
        candidate_roi = roi_metrics(profits)
        report[sport] = {
            "unique_settled_games": len(rows),
            "home_cover_wins_losses_pushes": dict(sorted(outcome_counts.items())),
            "candidate_vs_frozen_market_margin_errors": margin_comparison,
            "candidate_home_cover_probability": probability_metrics(
                candidate_home_probabilities
            ),
            "paired_market_home_cover_probability": probability_metrics(
                market_home_probabilities
            ),
            "paired_candidate_vs_market_probability": paired_probability_comparison,
            "candidate_calibration_intercept_slope": _calibration_intercept_slope(
                candidate_home_probabilities
            ),
            "candidate_actual_price_unit_roi": candidate_roi,
            "promotion_progress": {
                "margin_games": {
                    "completed": len(rows),
                    "required": 200,
                },
                "cover_probability_nonpush_games": {
                    "completed": len(candidate_home_probabilities),
                    "required": 200,
                },
                "paired_probability_games": {
                    "completed": paired_probability_comparison["sample_size"],
                    "required": 200,
                },
                "priced_candidate_selections": {
                    "completed": len(profits),
                    "required": 200,
                },
                "minimum_prior_unique_forecast_errors": {
                    "observed_minimum": min(calibration_history_counts, default=0),
                    "required_per_probability": 30,
                    "all_probabilities_meet_requirement": all(
                        value >= 30 for value in calibration_history_counts
                    ),
                },
                "paired_market_brier_gate_passed": paired_probability_comparison[
                    "promotion_brier_gate_passed"
                ],
                "paired_market_log_loss_gate_passed": paired_probability_comparison[
                    "promotion_log_loss_gate_passed"
                ],
                "paired_market_margin_gate_passed": bool(
                    margin_comparison["sample_size"] >= 200
                    and margin_comparison["mae_delta_ci95"] is not None
                    and margin_comparison["mae_delta_ci95"][1] < 0
                ),
                "actual_price_roi_gate_passed": bool(
                    candidate_roi["sample_size"] >= 200
                    and candidate_roi["unit_roi_ci95"] is not None
                    and candidate_roi["unit_roi_ci95"][0] > 0
                ),
                "complete_season_observed": False,
                "auto_promotion": False,
            },
        }
    return report


def _attempt_coverage(attempts: Iterable[dict]) -> dict:
    by_sport: dict[str, dict] = defaultdict(
        lambda: {
            "attempt_count": 0,
            "latest_by_game": {},
            "earliest_available_by_game": {},
            "unverified_receipt_attempts": 0,
        }
    )
    for row in attempts:
        if (
            row.get("record_type") == "candidate_forecast_attempt"
            and row.get("protocol_version") == PROTOCOL_VERSION
            and row.get("candidate_model_version") == MODEL_VERSION
        ):
            state = by_sport[row["sport"]]
            state["attempt_count"] += 1
            game_id = int(row["game_id"])
            current = state["latest_by_game"].get(game_id)
            if (
                current is None
                or row["prediction_timestamp"] > current["prediction_timestamp"]
            ):
                state["latest_by_game"][game_id] = row
            provenance_valid = _attempt_receipt_provenance_is_valid(row)
            if not provenance_valid:
                state["unverified_receipt_attempts"] += 1
            if (
                provenance_valid
                and row.get("candidate_margin_available")
                and row["kickoff"] > row["prediction_timestamp"]
            ):
                first = state["earliest_available_by_game"].get(game_id)
                if (
                    first is None
                    or row["prediction_timestamp"] < first["prediction_timestamp"]
                ):
                    state["earliest_available_by_game"][game_id] = row
    result = {}
    for sport, state in sorted(by_sport.items()):
        latest_by_game = state["latest_by_game"]
        earliest_available_by_game = state["earliest_available_by_game"]
        rejections = Counter(
            reason
            for row in latest_by_game.values()
            for reason in row.get("rejection_reasons", [])
        )
        rejections.update(
            {
                "unverified_score_receipt_provenance": sum(
                    not _attempt_receipt_provenance_is_valid(row)
                    for row in latest_by_game.values()
                )
            }
        )
        result[sport] = {
            "attempt_count": state["attempt_count"],
            "unique_games": len(latest_by_game),
            "unverified_receipt_attempts": state["unverified_receipt_attempts"],
            "primary_margin_games": len(earliest_available_by_game),
            "primary_probability_games": sum(
                row.get("cover_probability") is not None
                for row in earliest_available_by_game.values()
            ),
            "latest_attempt_rejections": dict(sorted(rejections.items())),
        }
    return result


def build_daily_coverage(
    db: Session,
    *,
    attempts: Iterable[dict],
    settlement_events: list[dict],
    run_log: list[dict],
    shadow_scores_path: Path,
    generated_at: datetime,
    current_run_id: str | None = None,
) -> dict:
    collection = build_collection_coverage(db)
    observations = _score_observations(db, shadow_scores_path=shadow_scores_path)
    valid_history: dict[str, list[TimestampedScore]] = defaultdict(list)
    for row in observations:
        if (
            row.kickoff < generated_at
            and row.observed_at < generated_at
            and row.status.strip().lower() in {"final", "completed"}
            and row.home_score is not None
            and row.away_score is not None
            and math.isfinite(float(row.home_score))
            and math.isfinite(float(row.away_score))
            and row.neutral_site is not None
        ):
            valid_history[row.sport].append(row)
    collection_by_sport = {row["sport"]: row for row in collection["sports"]}
    for sport in sorted(set(collection_by_sport) | set(valid_history)):
        score_rows = valid_history.get(sport, [])
        collection_by_sport.setdefault(sport, {"sport": sport})
        collection_by_sport[sport]["timestamped_scoring_history"] = {
            "unique_games": len({row.game_id for row in score_rows}),
            "known_site_games": len(
                {row.game_id for row in score_rows if row.neutral_site is not None}
            ),
            "providers": dict(
                sorted(
                    Counter(
                        row.source_provider or "unknown" for row in score_rows
                    ).items()
                )
            ),
            "latest_receipt_at": (
                max(row.observed_at for row in score_rows).isoformat()
                if score_rows
                else None
            ),
        }

    record_runs = [row for row in run_log if row.get("job") == "record"]
    successful_records = [row for row in record_runs if row.get("status") == "success"]
    evaluator_runs = [
        row for row in run_log if row.get("job") in {"evaluate", "coverage"}
    ]
    latest_record = max(
        record_runs,
        key=lambda row: row.get("started_at", ""),
        default=None,
    )
    latest_success = max(
        successful_records,
        key=lambda row: row.get("finished_at", ""),
        default=None,
    )
    latest_evaluation = max(
        evaluator_runs,
        key=lambda row: row.get("finished_at", ""),
        default=None,
    )
    unique_primary = _headline_events(settlement_events)
    return {
        "record_type": "daily_prospective_coverage",
        "protocol_version": PROTOCOL_VERSION,
        "candidate_model_version": MODEL_VERSION,
        "generated_at": generated_at.astimezone(UTC).isoformat(),
        "read_only_database": True,
        "recorder": {
            "latest_run": latest_record,
            "last_successful_run": latest_success,
            "failure_count": sum(row.get("status") == "failure" for row in record_runs),
            "attempts_by_sport": _attempt_coverage(attempts),
        },
        "evaluation": {
            "latest_scheduler_run": latest_evaluation,
            "newly_settled_games_this_run": sum(
                row.get("record_type") == "prospective_settlement_evidence"
                and row.get("run_id") == current_run_id
                and not row.get("is_score_correction")
                for row in settlement_events
            ),
            "unique_settled_games": len(unique_primary),
            "score_correction_events": sum(
                row.get("is_score_correction") for row in settlement_events
            ),
            "by_sport": build_evaluation_metrics(settlement_events),
        },
        "collection_coverage": list(collection_by_sport.values()),
        "candidate_activation_enabled": False,
        "customer_recommendation": False,
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def run_settlement_job(
    db: Session,
    *,
    attempts_dir: Path,
    shadow_scores_path: Path,
    settlements_path: Path,
    as_of: datetime,
    run_id: str,
) -> dict:
    attempts = _json_rows(attempts_dir)
    events = _load_settlement_events(settlements_path)
    observations = _score_observations(db, shadow_scores_path=shadow_scores_path)
    additions, latest = build_settlement_events(
        attempts,
        observations,
        as_of=as_of,
        existing_events=events,
    )
    for row in additions:
        row["run_id"] = run_id
    _append_jsonl(settlements_path, additions)
    updated = events + additions
    return {
        "run_id": run_id,
        "new_evidence_records": len(additions),
        "newly_settled_games": sum(not row["is_score_correction"] for row in additions),
        "score_correction_records": sum(
            row["is_score_correction"] for row in additions
        ),
        "headline_unique_settled_games": len(latest),
        "metrics": build_evaluation_metrics(updated),
        "settlement_file": str(settlements_path),
    }


def run_coverage_job(
    db: Session,
    *,
    attempts_dir: Path,
    shadow_scores_path: Path,
    settlements_path: Path,
    run_log_path: Path,
    coverage_path: Path,
    as_of: datetime,
    run_id: str,
) -> dict:
    attempts = _json_rows(attempts_dir)
    settlements = _load_settlement_events(settlements_path)
    run_log = _read_jsonl(run_log_path)
    report = build_daily_coverage(
        db,
        attempts=attempts,
        settlement_events=settlements,
        run_log=run_log,
        shadow_scores_path=shadow_scores_path,
        generated_at=as_of,
        current_run_id=run_id,
    )
    report["run_id"] = run_id
    known_runs = {row.get("run_id") for row in _read_jsonl(coverage_path)}
    if run_id not in known_runs:
        _append_jsonl(coverage_path, [report])
    return {
        "run_id": run_id,
        "coverage_report_written": run_id not in known_runs,
        "unique_settled_games": report["evaluation"]["unique_settled_games"],
        "coverage_file": str(coverage_path),
    }


def main() -> None:
    job = os.environ.get("TEAM_SCORING_JOB")
    run_id = os.environ.get("TEAM_SCORING_RUN_ID")
    root_value = os.environ.get("TEAM_SCORING_EVAL_DIR")
    if job not in {"evaluate", "coverage"} or not run_id or not root_value:
        raise RuntimeError(
            "Set valid TEAM_SCORING_JOB, TEAM_SCORING_RUN_ID, and TEAM_SCORING_EVAL_DIR"
        )
    root = Path(root_value)
    attempts_dir = root
    shadow_scores_path = root / "cfbd-score-observations.jsonl"
    settlements_path = root / "settlements.jsonl"
    as_of = datetime.now(UTC)
    with SessionLocal() as db:
        try:
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                from sqlalchemy import text

                db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                db.execute(text("SET TRANSACTION READ ONLY"))
            if job == "evaluate":
                report = run_settlement_job(
                    db,
                    attempts_dir=attempts_dir,
                    shadow_scores_path=shadow_scores_path,
                    settlements_path=settlements_path,
                    as_of=as_of,
                    run_id=run_id,
                )
            else:
                report = run_coverage_job(
                    db,
                    attempts_dir=attempts_dir,
                    shadow_scores_path=shadow_scores_path,
                    settlements_path=settlements_path,
                    run_log_path=root / "scheduler-runs.jsonl",
                    coverage_path=root / "coverage-reports.jsonl",
                    as_of=as_of,
                    run_id=run_id,
                )
        finally:
            db.rollback()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
