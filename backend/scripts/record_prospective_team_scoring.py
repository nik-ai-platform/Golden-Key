from __future__ import annotations

import gzip
import json
import math
import os
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.odds import Odds
from app.models.team import Team
from app.services.team_scoring_evaluation import select_positive_ev_side
from app.services.team_scoring_forecast import (
    ACTIVATION_ENABLED,
    MIN_CALIBRATION_ERRORS,
    MIN_TEAM_GAMES,
    MIN_TRAINING_GAMES,
    MODEL_VERSION,
    RIDGE_PENALTY,
    TimestampedScore,
    available_scores_as_of,
    estimate_cover_probabilities,
    forecast_home_margin,
)

PROTOCOL_VERSION = "TEAM-SCORING-PROSPECTIVE-1.0"
PROSPECTIVE_PERIOD_START = datetime(2026, 10, 9, 23, 49, 28, tzinfo=UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _db_time(value: datetime) -> datetime:
    return _utc(value).replace(tzinfo=None)


def _valid_score(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) >= 0


def _valid_american_price(value: int | None) -> bool:
    return value is not None and not isinstance(value, bool) and abs(value) >= 100


def _score_observations(
    db: Session,
    *,
    shadow_scores_path: Path | None = None,
) -> list[TimestampedScore]:
    rows = (
        db.query(GameResultObservation, Game)
        .join(
            Game,
            Game.id == GameResultObservation.game_id,
        )
        .all()
    )
    observations = [
        TimestampedScore(
            game_id=observation.game_id,
            sport=(game.sport or "").upper(),
            home_team_id=game.home_team_id,
            away_team_id=game.away_team_id,
            kickoff=_utc(game.game_date),
            observed_at=_utc(observation.observed_at),
            neutral_site=game.neutral_site,
            home_score=observation.home_score,
            away_score=observation.away_score,
            status=observation.status,
            observation_id=observation.id,
            source_provider=observation.provider,
            source_game_id=(
                str(game.provider_game_id) if game.provider_game_id else None
            ),
            source_updated_at=(
                _utc(observation.source_updated_at)
                if observation.source_updated_at
                else None
            ),
            receipt_basis="provider_observed_at",
        )
        for observation, game in rows
        if (observation.provider or "").lower() != "cfbd"
    ]
    if shadow_scores_path is not None and shadow_scores_path.exists():
        with shadow_scores_path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                observations.append(
                    TimestampedScore(
                        game_id=int(row["game_id"]),
                        sport=str(row["sport"]).upper(),
                        home_team_id=int(row["home_team_id"]),
                        away_team_id=int(row["away_team_id"]),
                        kickoff=_utc(datetime.fromisoformat(row["kickoff"])),
                        observed_at=_utc(datetime.fromisoformat(row["observed_at"])),
                        neutral_site=row.get("neutral_site"),
                        home_score=row.get("home_score"),
                        away_score=row.get("away_score"),
                        status=str(row["status"]),
                        observation_id=int(row["shadow_observation_id"]),
                        source_provider=str(row["provider"]),
                        source_game_id=str(row["provider_game_id"]),
                        source_updated_at=(
                            _utc(datetime.fromisoformat(row["source_updated_at"]))
                            if row.get("source_updated_at")
                            else None
                        ),
                        receipt_basis=str(
                            row.get("receipt_basis", "shadow_import_receipt")
                        ),
                    )
                )
    return observations


def _target_quotes(db: Session, as_of: datetime) -> dict[int, Odds]:
    rows = (
        db.query(Odds)
        .join(Game, Game.id == Odds.game_id)
        .filter(Odds.created_at < _db_time(as_of), Game.game_date > _db_time(as_of))
        .order_by(Odds.created_at.desc(), Odds.id.desc())
        .all()
    )
    latest: dict[int, Odds] = {}
    for row in rows:
        latest.setdefault(row.game_id, row)
    return latest


def _settled_prior_errors(
    prior_records: list[dict],
    observations: list[TimestampedScore],
    *,
    sport: str,
    as_of: datetime,
) -> list[dict]:
    records_by_game: dict[int, dict] = {}
    for record in prior_records:
        if (
            record.get("sport") != sport
            or record.get("candidate_model_version") != MODEL_VERSION
            or not record.get("candidate_margin_available")
            or not isinstance(record.get("candidate_home_margin"), (int, float))
        ):
            continue
        game_id = record.get("game_id")
        if not isinstance(game_id, int):
            continue
        predicted_at = datetime.fromisoformat(record["prediction_timestamp"])
        if _utc(predicted_at) >= as_of:
            continue
        current = records_by_game.get(game_id)
        if (
            current is None
            or record["prediction_timestamp"] < current["prediction_timestamp"]
        ):
            records_by_game[game_id] = record

    truth_by_game: dict[int, TimestampedScore] = {}
    for observation in observations:
        if (
            observation.sport != sport
            or observation.observed_at >= as_of
            or observation.status.strip().lower() not in {"final", "completed"}
            or not _valid_score(observation.home_score)
            or not _valid_score(observation.away_score)
        ):
            continue
        record = records_by_game.get(observation.game_id)
        if record is None:
            continue
        predicted_at = _utc(datetime.fromisoformat(record["prediction_timestamp"]))
        if observation.observed_at <= predicted_at:
            continue
        previous = truth_by_game.get(observation.game_id)
        if previous is None or (
            observation.observed_at,
            observation.observation_id,
        ) > (
            previous.observed_at,
            previous.observation_id,
        ):
            truth_by_game[observation.game_id] = observation

    errors = []
    for game_id, observation in sorted(truth_by_game.items()):
        record = records_by_game[game_id]
        actual_margin = float(observation.home_score) - float(observation.away_score)
        candidate_margin = float(record["candidate_home_margin"])
        errors.append(
            {
                "game_id": game_id,
                "forecast_timestamp": record["prediction_timestamp"],
                "candidate_home_margin": candidate_margin,
                "actual_home_margin": actual_margin,
                "error": actual_margin - candidate_margin,
                "score_observation_id": observation.observation_id,
                "score_observed_at": observation.observed_at.isoformat(),
            }
        )
    return errors


def build_prospective_records(
    db: Session,
    *,
    as_of: datetime,
    prior_records: list[dict] | None = None,
    shadow_scores_path: Path | None = None,
) -> list[dict]:
    cutoff = _utc(as_of)
    prior_records = prior_records or []
    observations = _score_observations(db, shadow_scores_path=shadow_scores_path)
    quotes = _target_quotes(db, cutoff)
    targets = (
        db.query(Game)
        .filter(
            Game.game_date > _db_time(cutoff),
            Game.status.notin_(("final", "completed", "canceled", "cancelled", "void")),
        )
        .order_by(Game.game_date, Game.sport, Game.id)
        .all()
    )
    calibration_by_sport: dict[str, list[dict]] = defaultdict(list)
    for sport in sorted({(game.sport or "").upper() for game in targets}):
        calibration_by_sport[sport] = _settled_prior_errors(
            prior_records,
            observations,
            sport=sport,
            as_of=cutoff,
        )

    records = []
    for game in targets:
        sport = (game.sport or "").upper()
        quote = quotes.get(game.id)
        reasons: list[str] = []
        if quote is None:
            reasons.append("no_pre_timestamp_odds_snapshot")
        elif (
            quote.spread_home is None
            or quote.spread_away is None
            or not math.isfinite(float(quote.spread_home))
            or not math.isfinite(float(quote.spread_away))
            or not math.isclose(
                float(quote.spread_home),
                -float(quote.spread_away),
                rel_tol=0,
                abs_tol=1e-6,
            )
        ):
            reasons.append("missing_or_noncomplementary_frozen_spread")
        if game.neutral_site is None:
            reasons.append("target_neutral_site_unknown")

        history = available_scores_as_of(
            observations,
            sport=sport,
            as_of=cutoff,
            exclude_game_id=game.id,
        )
        appearances: dict[int, int] = defaultdict(int)
        for item in history:
            appearances[item.home_team_id] += 1
            appearances[item.away_team_id] += 1
        if len(history) < MIN_TRAINING_GAMES:
            reasons.append("below_minimum_total_history")
        if appearances.get(game.home_team_id, 0) < MIN_TEAM_GAMES:
            reasons.append("below_minimum_home_team_history")
        if appearances.get(game.away_team_id, 0) < MIN_TEAM_GAMES:
            reasons.append("below_minimum_away_team_history")

        candidate = None
        if not reasons:
            candidate = forecast_home_margin(
                observations,
                sport=sport,
                home_team_id=game.home_team_id,
                away_team_id=game.away_team_id,
                neutral_site=game.neutral_site,
                as_of=cutoff,
                target_game_id=game.id,
            )
            if candidate is None:
                reasons.append("forecast_fit_unavailable")

        price_pair_available = bool(
            quote is not None
            and _valid_american_price(quote.spread_home_price)
            and _valid_american_price(quote.spread_away_price)
        )
        probability = None
        probability_reasons = []
        calibration = calibration_by_sport[sport]
        if (
            candidate is not None
            and quote is not None
            and quote.spread_home is not None
        ):
            if len(calibration) < MIN_CALIBRATION_ERRORS:
                probability_reasons.append("insufficient_prior_settled_forecast_errors")
            else:
                probability = estimate_cover_probabilities(
                    forecast_home_margin=candidate.home_margin,
                    spread_home=float(quote.spread_home),
                    earlier_forecast_errors=(item["error"] for item in calibration),
                )
                if probability is None:
                    probability_reasons.append("cover_probability_unavailable")
        if candidate is not None and not price_pair_available:
            probability_reasons.append("paired_frozen_spread_prices_unavailable")
        shadow_selection = None
        shadow_selection_reasons = []
        if candidate is not None and probability is not None and price_pair_available:
            shadow_selection = select_positive_ev_side(
                probability,
                quote.spread_home_price,
                quote.spread_away_price,
            )
            if shadow_selection is None:
                shadow_selection_reasons.append("no_positive_expected_value")
        elif candidate is not None:
            shadow_selection_reasons.append("probability_or_price_pair_unavailable")

        team_rows = (
            db.query(Team.id, Team.name)
            .filter(Team.id.in_((game.home_team_id, game.away_team_id)))
            .all()
        )
        team_names = {team_id: name for team_id, name in team_rows}
        records.append(
            {
                "record_type": "candidate_forecast_attempt",
                "protocol_version": PROTOCOL_VERSION,
                "candidate_model_version": MODEL_VERSION,
                "candidate_activation_enabled": ACTIVATION_ENABLED,
                "customer_recommendation": False,
                "prediction_timestamp": cutoff.isoformat(),
                "game_id": game.id,
                "sport": sport,
                "kickoff": _utc(game.game_date).isoformat(),
                "home_team_id": game.home_team_id,
                "home_team": team_names.get(game.home_team_id),
                "away_team_id": game.away_team_id,
                "away_team": team_names.get(game.away_team_id),
                "neutral_site": game.neutral_site,
                "venue": {
                    "name": game.venue_name,
                    "city": game.venue_city,
                    "state": game.venue_state,
                },
                "history_observation_count": len(history),
                "history_observation_ids": [item.observation_id for item in history],
                "history_observation_inputs": [
                    {
                        "observation_id": item.observation_id,
                        "game_id": item.game_id,
                        "sport": item.sport,
                        "kickoff": item.kickoff.isoformat(),
                        "observed_at": item.observed_at.isoformat(),
                        "home_team_id": item.home_team_id,
                        "away_team_id": item.away_team_id,
                        "neutral_site": item.neutral_site,
                        "home_score": item.home_score,
                        "away_score": item.away_score,
                        "source_provider": item.source_provider,
                        "source_game_id": item.source_game_id,
                        "source_updated_at": (
                            item.source_updated_at.isoformat()
                            if item.source_updated_at
                            else None
                        ),
                        "receipt_basis": item.receipt_basis,
                    }
                    for item in history
                ],
                "history_latest_receipt_at": (
                    max(item.observed_at for item in history).isoformat()
                    if history
                    else None
                ),
                "frozen_odds_snapshot_id": quote.id if quote else None,
                "frozen_odds_snapshot_timestamp": (
                    _utc(quote.created_at).isoformat() if quote else None
                ),
                "sportsbook": quote.sportsbook if quote else None,
                "spread_home": quote.spread_home if quote else None,
                "spread_away": quote.spread_away if quote else None,
                "spread_home_price": quote.spread_home_price if quote else None,
                "spread_away_price": quote.spread_away_price if quote else None,
                "candidate_margin_available": candidate is not None,
                "candidate_home_margin": (candidate.home_margin if candidate else None),
                "candidate_training_games": (
                    candidate.training_games if candidate else None
                ),
                "candidate_home_team_history": (
                    candidate.home_team_games if candidate else None
                ),
                "candidate_away_team_history": (
                    candidate.away_team_games if candidate else None
                ),
                "ridge_penalty": RIDGE_PENALTY,
                "rejection_reasons": reasons,
                "cover_probability": (
                    {
                        "home_cover": probability.home_cover,
                        "away_cover": probability.away_cover,
                        "push": probability.push,
                        "calibration_games": probability.calibration_games,
                    }
                    if probability
                    else None
                ),
                "probability_calibration_sample": (
                    calibration if candidate is not None else []
                ),
                "probability_rejection_reasons": probability_reasons,
                "shadow_selection": (
                    {
                        "side": shadow_selection[0],
                        "expected_value_per_unit": shadow_selection[1],
                    }
                    if shadow_selection
                    else None
                ),
                "shadow_selection_rejection_reasons": shadow_selection_reasons,
            }
        )
    return records


def _load_prior_records(path: Path) -> list[dict]:
    record_files = [path] if path.is_file() else sorted(path.glob("attempts*"))
    records = []
    for record_file in record_files:
        opener = gzip.open if record_file.suffix == ".gz" else open
        with opener(record_file, "rt", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                if (
                    row.get("record_type") == "candidate_forecast_attempt"
                    and row.get("candidate_margin_available")
                    and row.get("candidate_model_version") == MODEL_VERSION
                    and _attempt_receipt_provenance_is_valid(row)
                ):
                    records.append(
                        {
                            key: row[key]
                            for key in (
                                "sport",
                                "candidate_model_version",
                                "candidate_margin_available",
                                "game_id",
                                "prediction_timestamp",
                                "candidate_home_margin",
                            )
                            if key in row
                        }
                    )
    return records


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


def _write_attempt_batch(
    directory: Path, run_id: str, records: list[dict]
) -> Path | None:
    if not records:
        return None
    if not run_id or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in run_id
    ):
        raise ValueError(
            "run_id must contain only letters, digits, hyphens, or underscores"
        )
    output = directory / f"attempts-{run_id}.jsonl.gz"
    if output.exists():
        return None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".attempts-", suffix=".tmp", dir=directory
    )
    os.fchmod(descriptor, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                for record in records:
                    compressed.write(
                        (
                            json.dumps(
                                record,
                                sort_keys=True,
                                separators=(",", ":"),
                            )
                            + "\n"
                        ).encode("utf-8")
                    )
            raw.flush()
            os.fsync(raw.fileno())
        if os.path.getsize(temporary_name) > 256 * 1024 * 1024:
            raise RuntimeError("Compressed prospective attempt batch exceeds 256 MiB")
        try:
            os.link(temporary_name, output)
        except FileExistsError:
            return None
        if os.name == "posix":
            directory_descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        return output
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main() -> None:
    output_value = os.environ.get("TEAM_SCORING_PROSPECTIVE_OUTPUT")
    if not output_value:
        raise RuntimeError("TEAM_SCORING_PROSPECTIVE_OUTPUT must be set")
    attempt_at = datetime.now(UTC)
    if attempt_at < PROSPECTIVE_PERIOD_START:
        raise RuntimeError("The prospective evaluation period has not started")
    output = Path(output_value)
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    previous = _load_prior_records(output)
    run_id = os.environ.get("TEAM_SCORING_RUN_ID") or datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    attempt_file = output / f"attempts-{run_id}.jsonl.gz"
    if attempt_file.exists():
        print(
            json.dumps(
                {"records_written": 0, "run_id": run_id, "already_recorded": True}
            )
        )
        return
    shadow_scores_value = os.environ.get("TEAM_SCORING_SHADOW_SCORES")
    shadow_scores_path = Path(shadow_scores_value) if shadow_scores_value else None
    with SessionLocal() as db:
        try:
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                db.execute(text("SET TRANSACTION READ ONLY"))
            records = build_prospective_records(
                db,
                as_of=attempt_at,
                prior_records=previous,
                shadow_scores_path=shadow_scores_path,
            )
        finally:
            db.rollback()
    for record in records:
        record["run_id"] = run_id
    stored = _write_attempt_batch(output, run_id, records)
    print(
        json.dumps(
            {
                "records_written": len(records) if stored else 0,
                "run_id": run_id,
                "output": str(stored) if stored else None,
                "already_recorded": stored is None,
            }
        )
    )


if __name__ == "__main__":
    main()
