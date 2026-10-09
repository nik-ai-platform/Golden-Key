from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import aliased

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.services.prediction_metric_contract import (
    parse_market,
    supported_metadata,
)
from app.services.team_scoring_evaluation import (
    ScoringForecastCase,
    evaluate_forecasts,
)
from app.services.team_scoring_forecast import (
    ACTIVATION_ENABLED,
    MIN_CALIBRATION_ERRORS,
    MIN_TEAM_GAMES,
    MIN_TRAINING_GAMES,
    MODEL_VERSION,
    RIDGE_PENALTY,
    TimestampedScore,
    available_scores_as_of,
    forecast_home_margin,
)
from app.services.team_scoring_walkforward import (
    GamePeriod,
    split_games_chronologically,
)


SUPPORTED_VERSIONS = ("NPI-4.0", "NPI-5.0")
SPORTS = ("NBA", "NCAAF", "NFL", "WNBA", "NCAAB")


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _valid_score(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) >= 0


def _line_band(value: float) -> str:
    line = abs(value)
    if line < 3.5:
        return "0-3"
    if line <= 7:
        return "3.5-7"
    if line <= 14:
        return "7.5-14"
    return "above-14"


def _picked_side_type(selection: str, spread_home: float) -> str:
    if selection not in {"HOME", "AWAY"}:
        return "NO_BET"
    favorite_side = "HOME" if spread_home < 0 else "AWAY"
    return "FAVORITE" if selection == favorite_side else "UNDERDOG"


def _price_pair_valid(odds: Odds) -> bool:
    return (
        odds.spread_home is not None
        and odds.spread_away is not None
        and math.isclose(float(odds.spread_home), -float(odds.spread_away), abs_tol=1e-6)
        and odds.spread_home_price not in (None, 0)
        and odds.spread_away_price not in (None, 0)
    )


def _load_inventory(db) -> tuple[list[TimestampedScore], Counter, list[dict]]:
    rows = (
        db.query(GameResultObservation, Game)
        .join(Game, Game.id == GameResultObservation.game_id)
        .order_by(GameResultObservation.observed_at, GameResultObservation.id)
        .all()
    )
    observations: list[TimestampedScore] = []
    summary: dict[str, dict] = defaultdict(
        lambda: {
            "observations": 0,
            "valid_final_observations": 0,
            "game_ids": set(),
            "team_ids": set(),
            "first_observed_at": None,
            "last_observed_at": None,
        }
    )
    for observation, game in rows:
        sport = (game.sport or "UNKNOWN").upper()
        stats = summary[sport]
        stats["observations"] += 1
        stats["game_ids"].add(game.id)
        stats["team_ids"].update((game.home_team_id, game.away_team_id))
        observed_at = _utc(observation.observed_at)
        if observed_at is not None:
            stats["first_observed_at"] = min(
                observed_at,
                stats["first_observed_at"] or observed_at,
            )
            stats["last_observed_at"] = max(
                observed_at,
                stats["last_observed_at"] or observed_at,
            )
        kickoff = _utc(game.game_date)
        if (
            (observation.status or "").strip().lower() in {"final", "completed"}
            and _valid_score(observation.home_score)
            and _valid_score(observation.away_score)
            and kickoff is not None
            and observed_at is not None
            and observed_at >= kickoff
        ):
            stats["valid_final_observations"] += 1
        if kickoff is None or observed_at is None:
            continue
        observations.append(
            TimestampedScore(
                game_id=game.id,
                sport=sport,
                home_team_id=game.home_team_id,
                away_team_id=game.away_team_id,
                kickoff=kickoff,
                observed_at=observed_at,
                neutral_site=game.neutral_site,
                home_score=observation.home_score,
                away_score=observation.away_score,
                status=observation.status or "",
                observation_id=observation.id,
            )
        )
    team_rows = db.query(Team.id, Team.sport, Team.league, Team.name).order_by(Team.id).all()
    team_identity_by_sport: dict[str, list[dict]] = defaultdict(list)
    observed_team_ids = {
        team_id
        for item in observations
        for team_id in (item.home_team_id, item.away_team_id)
    }
    for team_id, sport, league, name in team_rows:
        if team_id in observed_team_ids:
            team_identity_by_sport[(sport or "UNKNOWN").upper()].append(
                {"team_id": team_id, "league": league, "name": name}
            )
    inventory = []
    for sport in sorted(set(summary) | set(SPORTS)):
        values = summary[sport]
        inventory.append(
            {
                "sport": sport,
                "observations": values["observations"],
                "games": len(values["game_ids"]),
                "team_ids": len(values["team_ids"]),
                "valid_final_observations": values["valid_final_observations"],
                "team_identities": team_identity_by_sport.get(sport, []),
                "first_observed_at": (
                    values["first_observed_at"].isoformat()
                    if values["first_observed_at"] is not None
                    else None
                ),
                "last_observed_at": (
                    values["last_observed_at"].isoformat()
                    if values["last_observed_at"] is not None
                    else None
                ),
            }
        )
    return observations, Counter(), inventory


def _latest_truth_by_game(observations: list[TimestampedScore]) -> dict[int, TimestampedScore]:
    latest: dict[int, TimestampedScore] = {}
    for item in observations:
        previous = latest.get(item.game_id)
        if previous is None or (
            item.observed_at,
            item.observation_id,
        ) > (
            previous.observed_at,
            previous.observation_id,
        ):
            latest[item.game_id] = item
    return {
        game_id: item
        for game_id, item in latest.items()
        if item.status.strip().lower() in {"final", "completed"}
        and _valid_score(item.home_score)
        and _valid_score(item.away_score)
        and item.observed_at >= item.kickoff
    }


def _load_targets(db, observations: list[TimestampedScore]) -> tuple[list[dict], Counter]:
    counts: Counter = Counter()
    home_team = aliased(Team)
    away_team = aliased(Team)
    rows = (
        db.query(Prediction, Game, Odds, home_team, away_team)
        .join(Game, Game.id == Prediction.game_id)
        .outerjoin(Odds, Odds.id == Prediction.odds_snapshot_id)
        .join(home_team, home_team.id == Game.home_team_id)
        .join(away_team, away_team.id == Game.away_team_id)
        .filter(Prediction.model_version.in_(SUPPORTED_VERSIONS))
        .order_by(Prediction.id)
        .all()
    )
    counts["prediction_rows_scanned"] = len(rows)
    truth = _latest_truth_by_game(observations)
    canonical: dict[tuple[int, str], tuple] = {}

    for prediction, game, odds, home, away in rows:
        if parse_market(prediction.market) != "spread":
            counts["other_market"] += 1
            continue
        published_at = _utc(prediction.created_at)
        kickoff = _utc(game.game_date)
        if published_at is None or kickoff is None:
            counts["missing_prediction_or_kickoff_time"] += 1
            continue
        if published_at >= kickoff:
            counts["post_kickoff_or_retrospective_prediction"] += 1
            continue
        if odds is None or prediction.odds_snapshot_id is None:
            counts["missing_frozen_odds_snapshot"] += 1
            continue
        odds_created_at = _utc(odds.created_at)
        quote_observed_at = _utc(prediction.odds_observed_at)
        if odds_created_at is None or odds_created_at >= published_at:
            counts["frozen_quote_not_available_at_prediction_time"] += 1
            continue
        if quote_observed_at is not None and quote_observed_at >= published_at:
            counts["prediction_quote_timestamp_after_publication"] += 1
            continue
        if (
            (home.sport or "").upper() != (game.sport or "").upper()
            or (away.sport or "").upper() != (game.sport or "").upper()
            or home.id == away.id
        ):
            counts["team_identity_mismatch"] += 1
            continue
        if odds.spread_home is None or not math.isfinite(float(odds.spread_home)):
            counts["missing_or_invalid_frozen_spread"] += 1
            continue
        if game.id not in truth:
            counts["missing_timestamped_final_truth"] += 1
            continue
        result = truth[game.id]
        if result.observed_at <= published_at:
            counts["target_final_received_before_prediction"] += 1
            continue
        counts["target_final_received_after_prediction"] += 1
        if (
            selection := (prediction.selection or "").strip().upper()
        ) in {"HOME", "AWAY"} and prediction.line_value is not None:
            selected_snapshot_line = (
                float(odds.spread_home)
                if selection == "HOME"
                else float(odds.spread_away)
                if odds.spread_away is not None
                else None
            )
            if (
                selected_snapshot_line is None
                or not math.isclose(
                    float(prediction.line_value),
                    selected_snapshot_line,
                    abs_tol=1e-6,
                )
            ):
                counts["selected_prediction_line_mismatch"] += 1
                continue
        counts["pregame_frozen_spread_predictions"] += 1

        key = (game.id, prediction.model_version)
        previous = canonical.get(key)
        current_order = (
            int(supported_metadata(prediction.market, prediction.selection)),
            published_at,
            prediction.id,
        )
        previous_order = (
            (
                int(supported_metadata(previous[0].market, previous[0].selection)),
                _utc(previous[0].created_at),
                previous[0].id,
            )
            if previous is not None
            else None
        )
        if previous is None or current_order > previous_order:
            canonical[key] = (prediction, game, odds, home, away, result)
    counts["canonical_pregame_labeled_game_versions"] = len(canonical)
    counts["prediction_revisions_collapsed"] = (
        counts["pregame_frozen_spread_predictions"]
        - len(canonical)
    )
    targets = []
    for prediction, game, odds, home, away, result in canonical.values():
        selection = (prediction.selection or "").strip().upper()
        if selection not in {"HOME", "AWAY", "PASS"}:
            counts["unsupported_selections"] += 1
            continue
        spread_home = float(odds.spread_home)
        spread_away = (
            float(odds.spread_away) if odds.spread_away is not None else None
        )
        if _price_pair_valid(odds):
            counts["paired_spread_prices_available"] += 1
        else:
            counts["paired_spread_prices_missing_or_unmatched"] += 1
        sim_margin = prediction.simulation_margin
        incumbent_margin = (
            float(sim_margin) - spread_home
            if sim_margin is not None and math.isfinite(float(sim_margin))
            else None
        )
        targets.append(
            {
                "game_id": game.id,
                "sport": (game.sport or "UNKNOWN").upper(),
                "model_version": prediction.model_version,
                "kickoff": kickoff if (kickoff := _utc(game.game_date)) else None,
                "published_at": _utc(prediction.created_at),
                "home_team_id": home.id,
                "away_team_id": away.id,
                "neutral_site": game.neutral_site,
                "actual_home_margin": float(result.home_score) - float(result.away_score),
                "spread_home": spread_home,
                "spread_away": spread_away,
                "home_price": odds.spread_home_price,
                "away_price": odds.spread_away_price,
                "selection": selection,
                "line_value": prediction.line_value,
                "incumbent_home_margin": incumbent_margin,
                "final_observed_at": result.observed_at,
            }
        )
    return targets, counts


def _forecast_targets(
    targets: list[dict],
    observations: list[TimestampedScore],
    counts: Counter,
) -> list[dict]:
    forecasted = []
    for target in targets:
        history = available_scores_as_of(
            observations,
            sport=target["sport"],
            as_of=target["published_at"],
            exclude_game_id=target["game_id"],
        )
        counts[f"history_games_asof_{target['sport']}"] += len(history)
        appearances: Counter = Counter()
        for historical_game in history:
            appearances[historical_game.home_team_id] += 1
            appearances[historical_game.away_team_id] += 1
        home_history = appearances[target["home_team_id"]]
        away_history = appearances[target["away_team_id"]]
        counts[f"home_team_prior_games_total_{target['sport']}"] += home_history
        counts[f"away_team_prior_games_total_{target['sport']}"] += away_history
        model = forecast_home_margin(
            observations,
            sport=target["sport"],
            home_team_id=target["home_team_id"],
            away_team_id=target["away_team_id"],
            neutral_site=target["neutral_site"],
            as_of=target["published_at"],
            target_game_id=target["game_id"],
        )
        candidate_margin = model.home_margin if model is not None else None
        if model is None:
            if target["neutral_site"] is None:
                counts[f"candidate_unavailable_unknown_neutral_site_{target['sport']}"] += 1
            if len(history) < MIN_TRAINING_GAMES:
                counts[f"candidate_unavailable_minimum_total_games_{target['sport']}"] += 1
            if home_history < MIN_TEAM_GAMES:
                counts[f"candidate_unavailable_home_team_history_{target['sport']}"] += 1
            if away_history < MIN_TEAM_GAMES:
                counts[f"candidate_unavailable_away_team_history_{target['sport']}"] += 1
        else:
            counts[f"candidate_margin_available_{target['sport']}"] += 1
        target = dict(target)
        target["candidate_home_margin"] = candidate_margin
        target["candidate_history_games"] = model.training_games if model else len(history)
        target["candidate_home_team_games"] = model.home_team_games if model else None
        target["candidate_away_team_games"] = model.away_team_games if model else None
        target["candidate_model_version"] = MODEL_VERSION
        forecasted.append(target)
    return forecasted


def _make_case(target: dict, calibration_errors=(), incumbent_errors=()) -> ScoringForecastCase:
    paired_prices = (
        target["home_price"]
        if target["spread_away"] is not None
        and math.isclose(
            target["spread_home"],
            -target["spread_away"],
            abs_tol=1e-6,
        )
        and target["home_price"] not in (0, None)
        and target["away_price"] not in (0, None)
        else None
    )
    paired_away_price = target["away_price"] if paired_prices is not None else None
    return ScoringForecastCase(
        game_id=target["game_id"],
        sport=target["sport"],
        model_version=target["model_version"],
        kickoff_sort=target["kickoff"].timestamp(),
        published_sort=target["published_at"].timestamp(),
        actual_home_margin=target["actual_home_margin"],
        spread_home=target["spread_home"],
        spread_away=target["spread_away"],
        selection=target["selection"],
        spread_home_price=paired_prices,
        spread_away_price=paired_away_price,
        published_selection_price=(
            target["home_price"]
            if target["selection"] == "HOME" and target["home_price"] not in (None, 0)
            else target["away_price"]
            if target["selection"] == "AWAY" and target["away_price"] not in (None, 0)
            else None
        ),
        candidate_home_margin=target["candidate_home_margin"],
        incumbent_home_margin=target["incumbent_home_margin"],
        calibration_errors=tuple(calibration_errors),
        incumbent_calibration_errors=tuple(incumbent_errors),
    )


def _split_and_evaluate(targets: list[dict]) -> dict:
    periods_by_sport = {
        sport: split_games_chronologically(
            [
                GamePeriod(game["game_id"], game["kickoff"])
                for game in targets
                if game["sport"] == sport
            ]
        )
        for sport in sorted({game["sport"] for game in targets})
    }
    periods = {
        name: tuple(
            game_id
            for sport_periods in periods_by_sport.values()
            for game_id in sport_periods[name]
        )
        for name in ("training", "tuning", "final_test")
    }
    period_by_game = {
        game_id: period
        for period, game_ids in periods.items()
        for game_id in game_ids
    }
    tuning_rows = [
        item for item in targets if period_by_game.get(item["game_id"]) == "tuning"
    ]
    test_rows = [
        item for item in targets if period_by_game.get(item["game_id"]) == "final_test"
    ]

    test_cases_by_group: dict[tuple[str, str, str, str], list[ScoringForecastCase]] = defaultdict(list)
    test_coverage = Counter()
    for target in test_rows:
        earlier_tuning = [
            item for item in tuning_rows
            if item["sport"] == target["sport"]
            and item["published_at"] < target["published_at"]
        ]
        by_game: dict[int, dict] = {}
        for item in earlier_tuning:
            previous = by_game.get(item["game_id"])
            if previous is None or item["published_at"] > previous["published_at"]:
                by_game[item["game_id"]] = item
        candidate_errors = tuple(
            item["actual_home_margin"] - item["candidate_home_margin"]
            for item in by_game.values()
            if item["candidate_home_margin"] is not None
        )
        incumbent_errors = tuple(
            item["actual_home_margin"] - item["incumbent_home_margin"]
            for item in by_game.values()
            if item["incumbent_home_margin"] is not None
        )
        test_coverage["test_records"] += 1
        test_coverage[f"earlier_tuning_candidate_errors_{target['sport']}"] += len(candidate_errors)
        if target["candidate_home_margin"] is None:
            test_coverage[f"test_candidate_unavailable_{target['sport']}"] += 1
        case = _make_case(target, candidate_errors, incumbent_errors)
        pick_type = _picked_side_type(target["selection"], target["spread_home"])
        band_value = (
            abs(float(target["line_value"]))
            if target["line_value"] is not None
            else abs(target["spread_home"])
        )
        key = (target["sport"], target["model_version"], pick_type, _line_band(band_value))
        test_cases_by_group[key].append(case)

    reports = []
    for key in sorted(test_cases_by_group):
        sport, version, pick_type, spread_band = key
        reports.append(
            {
                "sport": sport,
                "model_version": version,
                "recorded_pick_type": pick_type,
                "selected_side_spread_band": spread_band,
                "metrics": evaluate_forecasts(test_cases_by_group[key]),
            }
        )
    return {
        "period_games": {
            sport: {name: len(games) for name, games in values.items()}
            for sport, values in periods_by_sport.items()
        },
        "period_game_totals": {name: len(values) for name, values in periods.items()},
        "final_test_results_by_sport_model_pick_and_line_band": reports,
        "test_coverage": dict(sorted(test_coverage.items())),
    }


def build_report(db) -> dict:
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
    db.execute(text("SET TRANSACTION READ ONLY"))
    observations, _, inventory = _load_inventory(db)
    targets, exclusions = _load_targets(db, observations)
    forecast_counts = Counter()
    targets = _forecast_targets(targets, observations, forecast_counts)
    split_report = _split_and_evaluate(targets)
    return {
        "candidate_model_version": MODEL_VERSION,
        "candidate_activation_enabled": ACTIVATION_ENABLED,
        "candidate_description": (
            "Ridge-regularized team offense/points-allowed ratings from "
            "timestamp-available completed scores, opponent strength, and learned "
            "home advantage; no NPI or sportsbook inputs enter margin forecast."
        ),
        "fixed_candidate_hyperparameters": {
            "ridge_penalty": RIDGE_PENALTY,
            "minimum_games_per_team": MIN_TEAM_GAMES,
            "minimum_prior_games": MIN_TRAINING_GAMES,
            "minimum_earlier_tuning_errors_for_cover_probabilities": MIN_CALIBRATION_ERRORS,
            "tuning_use": "error calibration only; no test-period model selection",
            "final_test_fraction": 0.2,
        },
        "source_observation_policy": (
            "Use the latest valid result observation whose actual observed_at and "
            "game kickoff are strictly before the prediction timestamp; never use "
            "source_updated_at or game date as a substitute receipt time."
        ),
        "observation_inventory_by_sport": inventory,
        "eligible_target_predictions": len(targets),
        "exclusions": dict(sorted(exclusions.items())),
        "candidate_coverage": dict(sorted(forecast_counts.items())),
        "split_and_final_test": split_report,
        "limitations": [
            "Target predictions are grouped by game before chronological split; no game can cross periods.",
            "The final test is scored only after model and ridge penalty were frozen in the versioned candidate.",
            "Tuning forecast errors are used only when their prediction timestamp precedes the test prediction timestamp.",
            "Whole-point pushes are a separate empirical outcome class and are not scored as wins or losses.",
            "ROI is reported only from paired frozen spread prices; missing provider prices are excluded, never imputed.",
            "Current final observation is the evaluation label; only receipt-timestamp-valid prior observations may train a forecast.",
            "This shadow evaluation does not insert predictions, results, model rows, picks, or optimizer candidates.",
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
