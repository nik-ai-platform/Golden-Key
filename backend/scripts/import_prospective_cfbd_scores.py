from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.game import Game
from app.models.game_provider_identity import GameProviderIdentity
from app.models.team_provider_identity import TeamProviderIdentity
from app.providers.cfbd_client import CFBDClient

PROVIDER = "cfbd"
SPORT = "NCAAF"
MATCH_WINDOW = timedelta(hours=6)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _set_read_only(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.execute(text("SET TRANSACTION READ ONLY"))


def _fingerprint(row: dict) -> str:
    payload = {
        key: row[key]
        for key in (
            "provider_game_id",
            "season",
            "kickoff",
            "home_team_id",
            "away_team_id",
            "provider_home_team_id",
            "provider_away_team_id",
            "home_score",
            "away_score",
            "status",
            "neutral_site",
            "venue_name",
            "venue_city",
            "venue_state",
            "source_updated_at",
        )
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _shadow_ids(provider_game_id: str, fingerprint: str) -> tuple[int, int]:
    digest = hashlib.sha256(
        f"{PROVIDER}:{provider_game_id}:{fingerprint}".encode()
    ).hexdigest()
    return -int(digest[:15], 16), -int(digest[15:30], 16)


def _load_existing(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    latest: dict[str, str] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                latest[str(row["provider_game_id"])] = str(row["payload_hash"])
    return latest


def _game_id_for(
    provider_game_id: str,
    kickoff: datetime,
    home_team_id: int,
    away_team_id: int,
    identity_games: dict[str, int],
    games: list[Game],
) -> tuple[int, str]:
    mapped = identity_games.get(provider_game_id)
    if mapped is not None:
        return mapped, "provider_game_identity"
    candidates = [
        game
        for game in games
        if game.home_team_id == home_team_id
        and game.away_team_id == away_team_id
        and abs(_utc(game.game_date) - kickoff) <= MATCH_WINDOW
    ]
    if len(candidates) == 1:
        return candidates[0].id, "unique_team_kickoff_match"
    digest = hashlib.sha256(f"{SPORT}:{provider_game_id}".encode()).hexdigest()
    return -int(digest[:15], 16), "provider_only_shadow_id"


def collect_scores(
    db: Session,
    *,
    seasons: tuple[int, ...],
    output: Path,
    client: CFBDClient,
) -> dict:
    _set_read_only(db)
    team_ids = {
        (str(provider_team_id), (sport or "").upper()): team_id
        for provider_team_id, sport, team_id in db.query(
            TeamProviderIdentity.provider_team_id,
            TeamProviderIdentity.sport,
            TeamProviderIdentity.team_id,
        )
        .filter(TeamProviderIdentity.provider == PROVIDER)
        .all()
    }
    identity_games = {
        str(provider_game_id): game_id
        for provider_game_id, game_id in (
            db.query(
                GameProviderIdentity.provider_game_id, GameProviderIdentity.game_id
            )
            .join(Game, Game.id == GameProviderIdentity.game_id)
            .filter(
                GameProviderIdentity.provider == PROVIDER,
                Game.sport == SPORT,
            )
            .all()
        )
    }
    games = db.query(Game).filter(Game.sport == SPORT).all()
    existing = _load_existing(output)
    additions = []
    counts: dict[str, Counter] = defaultdict(Counter)

    for season in seasons:
        source_games = client.get_games(season)
        receipt_at = datetime.now(UTC)
        for source_game in source_games:
            sport_counts = counts[SPORT]
            if not source_game.completed:
                sport_counts["not_completed"] += 1
                continue
            if (
                source_game.home_points is None
                or source_game.away_points is None
                or source_game.home_points < 0
                or source_game.away_points < 0
            ):
                sport_counts["invalid_score"] += 1
                continue
            if source_game.neutral_site is None:
                sport_counts["unknown_site"] += 1
                continue
            home_team_id = team_ids.get((str(source_game.home_id), SPORT))
            away_team_id = team_ids.get((str(source_game.away_id), SPORT))
            if home_team_id is None or away_team_id is None:
                sport_counts["unmapped_team_identity"] += 1
                continue
            if home_team_id == away_team_id:
                sport_counts["identical_canonical_teams"] += 1
                continue

            provider_game_id = str(source_game.id)
            game_id, match_method = _game_id_for(
                provider_game_id,
                _utc(source_game.start_date),
                home_team_id,
                away_team_id,
                identity_games,
                games,
            )
            row = {
                "record_type": "prospective_score_observation",
                "provider": PROVIDER,
                "provider_game_id": provider_game_id,
                "game_id": game_id,
                "season": season,
                "sport": SPORT,
                "kickoff": _utc(source_game.start_date).isoformat(),
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "provider_home_team_id": str(source_game.home_id),
                "provider_away_team_id": str(source_game.away_id),
                "provider_home_team": source_game.home_team,
                "provider_away_team": source_game.away_team,
                "home_score": source_game.home_points,
                "away_score": source_game.away_points,
                "status": "final",
                "neutral_site": source_game.neutral_site,
                "venue_name": source_game.venue_name,
                "venue_city": source_game.venue_city,
                "venue_state": source_game.venue_state,
                "observed_at": receipt_at.isoformat(),
                "receipt_basis": "shadow_import_receipt",
                "source_updated_at": (
                    _utc(source_game.source_updated_at).isoformat()
                    if source_game.source_updated_at
                    else None
                ),
                "team_mapping_method": match_method,
            }
            fingerprint = _fingerprint(row)
            if existing.get(provider_game_id) == fingerprint:
                sport_counts["already_captured"] += 1
                continue
            row["payload_hash"] = fingerprint
            row["shadow_game_id"], row["shadow_observation_id"] = _shadow_ids(
                provider_game_id, fingerprint
            )
            additions.append(row)
            existing[provider_game_id] = fingerprint
            sport_counts["captured"] += 1
            sport_counts[f"team_mapping:{match_method}"] += 1
            sport_counts[
                "neutral_site_true"
                if source_game.neutral_site
                else "neutral_site_false"
            ] += 1

    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.touch(mode=0o600, exist_ok=True)
    os.chmod(output.parent, 0o700)
    os.chmod(output, 0o600)
    if additions:
        descriptor = os.open(output, os.O_APPEND | os.O_WRONLY)
        try:
            payload = "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in additions
            ).encode("utf-8")
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("Could not append all CFBD shadow observations")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return {
        "seasons": list(seasons),
        "requests": len(seasons),
        "observations_appended": len(additions),
        "sports": {
            sport: dict(sorted(values.items()))
            for sport, values in sorted(counts.items())
        },
    }


def main() -> None:
    seasons_value = os.environ.get("TEAM_SCORING_CFB_SEASONS", "")
    output_value = os.environ.get("TEAM_SCORING_SHADOW_SCORES")
    if not seasons_value or not output_value:
        raise RuntimeError(
            "TEAM_SCORING_CFB_SEASONS and TEAM_SCORING_SHADOW_SCORES are required"
        )
    seasons = tuple(sorted({int(value) for value in seasons_value.split(",")}))
    if not seasons or any(
        season < 2000 or season > datetime.now(UTC).year for season in seasons
    ):
        raise ValueError("CFBD import seasons must be valid past or current years")
    with SessionLocal() as db:
        try:
            report = collect_scores(
                db,
                seasons=seasons,
                output=Path(output_value),
                client=CFBDClient(),
            )
        finally:
            db.rollback()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
