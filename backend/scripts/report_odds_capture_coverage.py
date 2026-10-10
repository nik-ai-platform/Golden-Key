from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.odds import Odds
from app.models.team import Team
from app.models.team_alias import TeamAlias
from app.models.team_provider_identity import TeamProviderIdentity


def _valid_price(value: int | None) -> bool:
    return value is not None and not isinstance(value, bool) and abs(value) >= 100


def _new_market_counts() -> dict:
    return {
        "quote_snapshots": 0,
        "complementary_line_snapshots": 0,
        "paired_price_snapshots": 0,
        "one_price_missing_or_invalid": 0,
        "both_prices_missing_or_invalid": 0,
        "noncomplementary_line_snapshots": 0,
        "first_paired_snapshot_at": None,
        "quote_snapshots_since_first_pair": 0,
        "paired_price_snapshots_since_first_pair": 0,
        "_tie_timestamp": None,
        "_tie_quotes": 0,
    }


def _add_market_snapshot(
    counts: dict,
    *,
    created_at: datetime,
    has_line: bool,
    complementary_line: bool,
    prices: tuple[int | None, int | None],
) -> None:
    if (
        counts["first_paired_snapshot_at"] is None
        and counts["_tie_timestamp"] != created_at
    ):
        counts["_tie_timestamp"] = created_at
        counts["_tie_quotes"] = 0
    if has_line:
        counts["quote_snapshots"] += 1
        if counts["first_paired_snapshot_at"] is None:
            counts["_tie_quotes"] += 1
        elif created_at >= counts["first_paired_snapshot_at"]:
            counts["quote_snapshots_since_first_pair"] += 1
    if not has_line:
        return
    if complementary_line:
        counts["complementary_line_snapshots"] += 1
    else:
        counts["noncomplementary_line_snapshots"] += 1
        return

    valid_prices = tuple(_valid_price(price) for price in prices)
    if not all(valid_prices):
        if sum(not valid for valid in valid_prices) == 1:
            counts["one_price_missing_or_invalid"] += 1
        else:
            counts["both_prices_missing_or_invalid"] += 1
        return

    counts["paired_price_snapshots"] += 1
    if counts["first_paired_snapshot_at"] is None:
        counts["first_paired_snapshot_at"] = created_at
        counts["quote_snapshots_since_first_pair"] = counts["_tie_quotes"]
        counts["paired_price_snapshots_since_first_pair"] = 1
    elif created_at >= counts["first_paired_snapshot_at"]:
        counts["paired_price_snapshots_since_first_pair"] += 1


def _market_report(counts: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in counts.items()
        if not key.startswith("_")
        and key
        not in {
            "first_paired_snapshot_at",
            "quote_snapshots_since_first_pair",
            "paired_price_snapshots_since_first_pair",
        }
    }


def _market_since_report(counts: dict) -> dict:
    first_pair_at = counts["first_paired_snapshot_at"]
    return {
        "first_paired_snapshot_at": (
            first_pair_at.isoformat() if first_pair_at else None
        ),
        "quote_snapshots_since_first_pair": counts["quote_snapshots_since_first_pair"],
        "paired_price_snapshots_since_first_pair": counts[
            "paired_price_snapshots_since_first_pair"
        ],
    }


def build_report(db: Session) -> dict:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.execute(text("SET TRANSACTION READ ONLY"))

    odds_by_sport: dict[str, dict] = defaultdict(
        lambda: {
            "odds_snapshots": 0,
            "spread": _new_market_counts(),
            "total": _new_market_counts(),
        }
    )
    odds_query = (
        db.query(
            Odds.spread_home,
            Odds.spread_away,
            Odds.spread_home_price,
            Odds.spread_away_price,
            Odds.total,
            Odds.total_over_price,
            Odds.total_under_price,
            Odds.created_at,
            Game.sport,
        )
        .join(Game, Game.id == Odds.game_id)
        .order_by(func.upper(Game.sport), Odds.created_at, Odds.id)
        .yield_per(2000)
    )
    for (
        spread_home,
        spread_away,
        spread_home_price,
        spread_away_price,
        total_line,
        total_over_price,
        total_under_price,
        created_at,
        sport_value,
    ) in odds_query:
        sport = (sport_value or "").upper()
        sport_counts = odds_by_sport[sport]
        sport_counts["odds_snapshots"] += 1
        _add_market_snapshot(
            sport_counts["spread"],
            created_at=created_at,
            has_line=spread_home is not None or spread_away is not None,
            complementary_line=(
                spread_home is not None
                and spread_away is not None
                and math.isclose(
                    spread_home,
                    -spread_away,
                    rel_tol=0,
                    abs_tol=1e-6,
                )
            ),
            prices=(spread_home_price, spread_away_price),
        )
        _add_market_snapshot(
            sport_counts["total"],
            created_at=created_at,
            has_line=total_line is not None,
            complementary_line=total_line is not None,
            prices=(total_over_price, total_under_price),
        )

    game_counts: dict[str, Counter] = defaultdict(Counter)
    for sport_value, neutral_site, venue_name, venue_city, venue_state in (
        db.query(
            Game.sport,
            Game.neutral_site,
            Game.venue_name,
            Game.venue_city,
            Game.venue_state,
        )
        .order_by(Game.id)
        .yield_per(2000)
    ):
        sport = (sport_value or "").upper()
        counts = game_counts[sport]
        counts["games"] += 1
        counts["neutral_site_true"] += neutral_site is True
        counts["neutral_site_false"] += neutral_site is False
        counts["neutral_site_unknown"] += neutral_site is None
        counts["games_with_explicit_venue"] += any(
            isinstance(value, str) and value.strip()
            for value in (venue_name, venue_city, venue_state)
        )

    team_counts: Counter = Counter()
    team_sports: dict[int, str] = {}
    for team_id, sport_value in db.query(Team.id, Team.sport).yield_per(2000):
        sport = (sport_value or "").upper()
        team_sports[team_id] = sport
        team_counts[sport] += 1
    identities: dict[int, set[str]] = defaultdict(set)
    for team_id, sport_value in db.query(
        TeamProviderIdentity.team_id,
        TeamProviderIdentity.sport,
    ).yield_per(2000):
        identities[team_id].add((sport_value or "").upper())
    alias_team_ids = {
        team_id for (team_id,) in db.query(TeamAlias.team_id).distinct().yield_per(2000)
    }
    team_identity_counts: dict[str, Counter] = defaultdict(Counter)
    for team_id, sport in team_sports.items():
        identity_sports = identities.get(team_id, set())
        team_identity_counts[sport][
            "team_ids_with_matching_sport_provider_identity"
        ] += sport in identity_sports
        team_identity_counts[sport]["team_ids_with_alias"] += team_id in alias_team_ids
        team_identity_counts[sport]["team_ids_with_cross_sport_provider_identity"] += (
            bool(identity_sports - {sport})
        )

    score_counts: dict[str, Counter] = defaultdict(Counter)
    for sport_value, observation_count, unique_games, latest_receipt in (
        db.query(
            Game.sport,
            func.count(GameResultObservation.id),
            func.count(func.distinct(GameResultObservation.game_id)),
            func.max(GameResultObservation.observed_at),
        )
        .join(Game, Game.id == GameResultObservation.game_id)
        .group_by(Game.sport)
        .all()
    ):
        sport = (sport_value or "").upper()
        score_counts[sport]["observations"] = observation_count
        score_counts[sport]["unique_games_with_observations"] = unique_games
        score_counts[sport]["latest_receipt_at"] = (
            latest_receipt.isoformat() if latest_receipt else None
        )
    provider_counts: dict[str, Counter] = defaultdict(Counter)
    for sport_value, provider, count in (
        db.query(
            Game.sport,
            GameResultObservation.provider,
            func.count(GameResultObservation.id),
        )
        .join(Game, Game.id == GameResultObservation.game_id)
        .group_by(Game.sport, GameResultObservation.provider)
        .all()
    ):
        provider_counts[(sport_value or "").upper()][provider or "unknown"] = count
    for sport_value, home_score, away_score in (
        db.query(
            Game.sport,
            GameResultObservation.home_score,
            GameResultObservation.away_score,
        )
        .join(Game, Game.id == GameResultObservation.game_id)
        .filter(
            func.lower(GameResultObservation.status).in_(("final", "completed")),
            GameResultObservation.home_score.is_not(None),
            GameResultObservation.away_score.is_not(None),
            GameResultObservation.home_score >= 0,
            GameResultObservation.away_score >= 0,
        )
        .yield_per(2000)
    ):
        if math.isfinite(float(home_score)) and math.isfinite(float(away_score)):
            score_counts[(sport_value or "").upper()][
                "valid_final_score_observations"
            ] += 1

    sports = sorted(
        set(odds_by_sport) | set(game_counts) | set(score_counts) | set(team_counts)
    )
    coverage = []
    for sport in sports:
        score_counts[sport].setdefault("observations", 0)
        score_counts[sport].setdefault("unique_games_with_observations", 0)
        score_counts[sport].setdefault("valid_final_score_observations", 0)
        score_counts[sport].setdefault("latest_receipt_at", None)
        team_identity_counts[sport].setdefault(
            "team_ids_with_matching_sport_provider_identity", 0
        )
        team_identity_counts[sport].setdefault("team_ids_with_alias", 0)
        team_identity_counts[sport].setdefault(
            "team_ids_with_cross_sport_provider_identity", 0
        )
        coverage.append(
            {
                "sport": sport,
                "odds_snapshots": odds_by_sport[sport]["odds_snapshots"],
                "spread": _market_report(odds_by_sport[sport]["spread"]),
                "total": _market_report(odds_by_sport[sport]["total"]),
                "spread_since_first_paired_capture": _market_since_report(
                    odds_by_sport[sport]["spread"]
                ),
                "total_since_first_paired_capture": _market_since_report(
                    odds_by_sport[sport]["total"]
                ),
                **{
                    key: game_counts[sport][key]
                    for key in (
                        "games",
                        "neutral_site_true",
                        "neutral_site_false",
                        "neutral_site_unknown",
                        "games_with_explicit_venue",
                    )
                },
                "team_ids": team_counts[sport],
                **team_identity_counts[sport],
                "score_history": {
                    **score_counts[sport],
                    "providers": dict(sorted(provider_counts[sport].items())),
                },
            }
        )
    return {
        "report_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "sports": coverage,
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
