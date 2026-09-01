import argparse
from datetime import UTC, datetime, timedelta

from app.database.session import SessionLocal
from app.models.game import Game
from app.services.final_score_settlement_service import FinalScoreSettlementService
from app.services.odds_provider_client import OddsProviderClient
from app.services.sport_mapping_service import SportMappingService


def _game_details(game: Game) -> str:
    return (
        f"local_game_id={game.id} provider_event_id={game.provider_game_id} "
        f"game_date={game.game_date} home_team={game.home_team.name} "
        f"away_team={game.away_team.name} status={game.status} "
        f"home_score={game.home_score} away_score={game.away_score} "
        f"completed_at={game.completed_at}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only recent game reconciliation diagnostic.")
    parser.add_argument("--sport", default="WNBA")
    parser.add_argument("--days", type=int, default=3)
    args = parser.parse_args()
    sport = args.sport.upper()
    days = max(1, args.days)
    now = datetime.now(UTC).replace(tzinfo=None)
    cutoff = now - timedelta(days=days)
    provider = OddsProviderClient()
    rows = provider.get_scores(
        SportMappingService().provider_key(sport),
        days_from=days,
    )
    rows_by_id = {row.get("id"): row for row in rows if row.get("id")}

    with SessionLocal() as db:
        games = (
            db.query(Game)
            .filter(Game.sport == sport, Game.game_date >= cutoff)
            .order_by(Game.game_date.asc())
            .all()
        )
        local_ids = {game.provider_game_id for game in games}
        for game in games:
            row = rows_by_id.get(game.provider_game_id)
            if row is None:
                state = "LOCAL_STALE" if game.game_date < now and game.status != "final" else "NOT_FINAL_AT_PROVIDER"
            elif row.get("completed") is not True:
                state = "NOT_FINAL_AT_PROVIDER"
            elif FinalScoreSettlementService._extract_scores(row) is None:
                state = "RECONCILIATION_ERROR"
            elif game.status == "final":
                state = "ALREADY_FINAL"
            else:
                state = "MATCHED_FINAL"
            print(f"{state} {_game_details(game)}")

        for row in rows:
            if row.get("completed") is True and row.get("id") not in local_ids:
                print(
                    "UNMATCHED_PROVIDER_EVENT "
                    f"provider_event_id={row.get('id')} "
                    f"home_team={row.get('home_team')} "
                    f"away_team={row.get('away_team')} "
                    f"commence_time={row.get('commence_time')}"
                )

        db.rollback()


if __name__ == "__main__":
    main()