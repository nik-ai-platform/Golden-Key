from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.odds import Odds
from app.models.team import Team
from app.models.team_alias import TeamAlias
from app.models.team_provider_identity import TeamProviderIdentity


def _valid_price(value: int | None) -> bool:
    return value is not None and not isinstance(value, bool) and abs(value) >= 100


def _valid_pair(row: Odds, market: str) -> bool:
    if market == "spread":
        return (
            row.spread_home is not None
            and row.spread_away is not None
            and math.isclose(
                row.spread_home,
                -row.spread_away,
                rel_tol=0,
                abs_tol=1e-6,
            )
            and _valid_price(row.spread_home_price)
            and _valid_price(row.spread_away_price)
        )
    return (
        row.total is not None
        and _valid_price(row.total_over_price)
        and _valid_price(row.total_under_price)
    )


def _capture_counts(rows: list[Odds], market: str) -> dict:
    if market == "spread":
        has_line = lambda row: row.spread_home is not None or row.spread_away is not None
        complementary = lambda row: (
            row.spread_home is not None
            and row.spread_away is not None
            and math.isclose(
                row.spread_home,
                -row.spread_away,
                rel_tol=0,
                abs_tol=1e-6,
            )
        )
        price_fields = ("spread_home_price", "spread_away_price")
    else:
        has_line = lambda row: row.total is not None
        complementary = has_line
        price_fields = ("total_over_price", "total_under_price")

    quotes = [row for row in rows if has_line(row)]
    paired = [row for row in quotes if _valid_pair(row, market)]
    complement_lines = [row for row in quotes if complementary(row)]
    unpaired = [row for row in complement_lines if row not in paired]
    return {
        "quote_snapshots": len(quotes),
        "complementary_line_snapshots": len(complement_lines),
        "paired_price_snapshots": len(paired),
        "one_price_missing_or_invalid": sum(
            sum(
                not _valid_price(getattr(row, field))
                for field in price_fields
            )
            == 1
            for row in unpaired
        ),
        "both_prices_missing_or_invalid": sum(
            all(
                not _valid_price(getattr(row, field))
                for field in price_fields
            )
            for row in unpaired
        ),
        "noncomplementary_line_snapshots": len(quotes) - len(complement_lines),
    }


def build_report(db: Session) -> dict:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.execute(text("SET TRANSACTION READ ONLY"))

    odds_by_sport: dict[str, list[Odds]] = defaultdict(list)
    for odds, sport in (
        db.query(Odds, Game.sport)
        .join(Game, Game.id == Odds.game_id)
        .order_by(Odds.created_at, Odds.id)
        .all()
    ):
        odds_by_sport[sport.upper()].append(odds)

    games_by_sport: dict[str, list[Game]] = defaultdict(list)
    for game in db.query(Game).all():
        games_by_sport[game.sport.upper()].append(game)

    teams = db.query(Team.id, Team.sport).all()
    team_sport = {team_id: (sport or "").upper() for team_id, sport in teams}
    identities: dict[int, set[str]] = defaultdict(set)
    for team_id, sport in db.query(
        TeamProviderIdentity.team_id,
        TeamProviderIdentity.sport,
    ).all():
        identities[team_id].add((sport or "").upper())
    alias_team_ids = {
        team_id for (team_id,) in db.query(TeamAlias.team_id).distinct().all()
    }

    sports = sorted(
        set(odds_by_sport) | set(games_by_sport) | set(team_sport.values())
    )
    coverage = []
    for sport in sports:
        rows = odds_by_sport[sport]
        games = games_by_sport[sport]
        ids = {team_id for team_id, team_value in team_sport.items() if team_value == sport}
        matched = {
            team_id
            for team_id in ids
            if sport in identities.get(team_id, set())
        }
        cross_sport = {
            team_id
            for team_id in ids
            if identities.get(team_id, set()) - {sport}
        }
        spread = _capture_counts(rows, "spread")
        total = _capture_counts(rows, "total")
        coverage.append(
            {
                "sport": sport,
                "odds_snapshots": len(rows),
                "spread": spread,
                "total": total,
                "spread_since_first_paired_capture": _since_first_pair(
                    rows, "spread"
                ),
                "total_since_first_paired_capture": _since_first_pair(
                    rows, "total"
                ),
                "games": len(games),
                "neutral_site_true": sum(game.neutral_site is True for game in games),
                "neutral_site_false": sum(game.neutral_site is False for game in games),
                "neutral_site_unknown": sum(game.neutral_site is None for game in games),
                "games_with_explicit_venue": sum(
                    any(
                        isinstance(value, str) and value.strip()
                        for value in (
                            game.venue_name,
                            game.venue_city,
                            game.venue_state,
                        )
                    )
                    for game in games
                ),
                "team_ids": len(ids),
                "team_ids_with_matching_sport_provider_identity": len(matched),
                "team_ids_with_alias": len(ids & alias_team_ids),
                "team_ids_with_cross_sport_provider_identity": len(cross_sport),
            }
        )
    return {
        "report_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "sports": coverage,
    }


def _since_first_pair(rows: list[Odds], market: str) -> dict:
    paired_rows = [row for row in rows if _valid_pair(row, market)]
    if not paired_rows:
        return {
            "first_paired_snapshot_at": None,
            "quote_snapshots_since_first_pair": 0,
            "paired_price_snapshots_since_first_pair": 0,
        }
    first_pair_at = min(row.created_at for row in paired_rows)
    if market == "spread":
        has_line = lambda row: row.spread_home is not None or row.spread_away is not None
    else:
        has_line = lambda row: row.total is not None
    since = [
        row
        for row in rows
        if row.created_at >= first_pair_at and has_line(row)
    ]
    return {
        "first_paired_snapshot_at": first_pair_at.isoformat(),
        "quote_snapshots_since_first_pair": len(since),
        "paired_price_snapshots_since_first_pair": sum(
            _valid_pair(row, market) for row in since
        ),
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
