from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import text

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.services.margin_forecast_candidate import (
    ACTIVATION_ENABLED,
    MODEL_VERSION,
    forecast_home_margin_from_spread,
)
from app.services.margin_forecast_validation import (
    MarginForecastObservation,
    evaluate_chronological_holdout,
)
from app.services.prediction_metric_contract import parse_market, supported_metadata


SUPPORTED_VERSIONS = ("NPI-4.0", "NPI-5.0")
HOLDOUT_FRACTION = 0.2


def _utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _valid_score(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value)) and value >= 0


def _eligible_observations(db) -> tuple[list[MarginForecastObservation], Counter]:
    counts: Counter = Counter()
    rows = (
        db.query(Prediction, Game, Odds)
        .join(Game, Game.id == Prediction.game_id)
        .outerjoin(Odds, Odds.id == Prediction.odds_snapshot_id)
        .filter(Prediction.model_version.in_(SUPPORTED_VERSIONS))
        .order_by(Prediction.id)
        .all()
    )
    counts["prediction_rows_scanned"] = len(rows)

    canonical: dict[tuple[int, str], tuple[Prediction, Game, Odds]] = {}
    for prediction, game, odds in rows:
        if parse_market(prediction.market) != "spread":
            counts["other_market"] += 1
            continue

        kickoff = _utc_naive(game.game_date)
        published_at = _utc_naive(prediction.created_at)
        if kickoff is None or published_at is None:
            counts["missing_publication_time"] += 1
            continue
        if published_at >= kickoff:
            counts["post_kickoff_or_retrospective"] += 1
            continue
        if odds is None or prediction.odds_snapshot_id is None:
            counts["missing_frozen_odds"] += 1
            continue
        if odds.spread_home is None or not math.isfinite(float(odds.spread_home)):
            counts["missing_or_invalid_home_spread"] += 1
            continue
        quote_time = _utc_naive(odds.created_at)
        prediction_quote_time = _utc_naive(prediction.odds_observed_at)
        if quote_time is None or quote_time >= kickoff:
            counts["quote_not_observed_before_kickoff"] += 1
            continue
        if prediction_quote_time is not None and prediction_quote_time >= kickoff:
            counts["prediction_quote_not_observed_before_kickoff"] += 1
            continue
        if (game.status or "").strip().lower() not in {"final", "completed"}:
            counts["game_not_final"] += 1
            continue
        if not _valid_score(game.home_score) or not _valid_score(game.away_score):
            counts["invalid_final_score"] += 1
            continue

        counts["pregame_eligible_rows"] += 1
        key = (game.id, prediction.model_version)
        previous = canonical.get(key)
        current_rank = (
            int(supported_metadata(prediction.market, prediction.selection)),
            published_at,
            prediction.id,
        )
        previous_rank = (
            (
                int(supported_metadata(previous[0].market, previous[0].selection)),
                _utc_naive(previous[0].created_at),
                previous[0].id,
            )
            if previous is not None
            else None
        )
        if previous is None or current_rank > previous_rank:
            canonical[key] = (prediction, game, odds)

    counts["pregame_canonical_predictions"] = len(canonical)
    counts["pregame_revisions_collapsed"] = (
        counts["pregame_eligible_rows"] - len(canonical)
    )
    result: list[MarginForecastObservation] = []
    for prediction, game, odds in canonical.values():
        spread_home = float(odds.spread_home)
        simulation_margin = prediction.simulation_margin
        incumbent_margin = (
            float(simulation_margin) - spread_home
            if simulation_margin is not None
            and math.isfinite(float(simulation_margin))
            else None
        )
        if incumbent_margin is None:
            counts["incumbent_margin_unavailable"] += 1
        if (prediction.selection or "").strip().upper() == "PASS":
            counts["pass_forecasts_included"] += 1
        result.append(
            MarginForecastObservation(
                game_id=game.id,
                kickoff=_utc_naive(game.game_date),
                published_at=_utc_naive(prediction.created_at),
                sport=(game.sport or "UNKNOWN").strip().upper(),
                model_version=prediction.model_version,
                actual_home_margin=float(game.home_score) - float(game.away_score),
                market_implied_home_margin=forecast_home_margin_from_spread(
                    spread_home
                ),
                incumbent_home_margin=incumbent_margin,
            )
        )
    return result, counts


def build_report(db) -> dict:
    db.execute(text("SET TRANSACTION READ ONLY"))
    observations, counts = _eligible_observations(db)

    latest_by_game: dict[int, MarginForecastObservation] = {}
    version_priority = {"NPI-4.0": 4, "NPI-5.0": 5}
    for item in observations:
        previous = latest_by_game.get(item.game_id)
        if previous is None or (
            item.published_at,
            version_priority.get(item.model_version, 0),
        ) > (
            previous.published_at,
            version_priority.get(previous.model_version, 0),
        ):
            latest_by_game[item.game_id] = item

    candidate_groups = []
    for sport in sorted({item.sport for item in latest_by_game.values()}):
        items = [item for item in latest_by_game.values() if item.sport == sport]
        candidate_groups.append(
            {
                "sport": sport,
                "market": "SPREAD",
                **evaluate_chronological_holdout(items, HOLDOUT_FRACTION),
            }
        )

    incumbent_groups = []
    for sport, version in sorted(
        {(item.sport, item.model_version) for item in observations}
    ):
        items = [
            item
            for item in observations
            if item.sport == sport and item.model_version == version
        ]
        incumbent_groups.append(
            {
                "sport": sport,
                "market": "SPREAD",
                "incumbent_model_version": version,
                **evaluate_chronological_holdout(items, HOLDOUT_FRACTION),
            }
        )

    return {
        "candidate_model_version": MODEL_VERSION,
        "candidate_activation_enabled": ACTIVATION_ENABLED,
        "candidate_kind": "frozen market-implied home margin; no fitted weights",
        "probabilities_or_bet_recommendations": False,
        "timestamp_gate": (
            "prediction publication and frozen quote must both predate kickoff"
        ),
        "heldout_fraction": HOLDOUT_FRACTION,
        "eligible_unique_games": len(latest_by_game),
        "eligible_canonical_version_records": len(observations),
        "exclusions_and_coverage": dict(sorted(counts.items())),
        "candidate_by_sport_market": candidate_groups,
        "incumbent_comparison_by_sport_market_version": incumbent_groups,
        "limitations": [
            "The candidate is a market-margin baseline, not an independent team-strength model.",
            "The history prefix is reported for chronological separation; no parameters are fitted.",
            "Historical labels use the current final Game scores, including any later corrections.",
            "Only spread-market records with a frozen pre-kickoff quote are evaluated.",
        ],
    }


def main() -> None:
    with SessionLocal() as db:
        try:
            report = build_report(db)
        finally:
            db.rollback()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
