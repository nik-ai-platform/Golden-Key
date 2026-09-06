import argparse
import json

from app.database.session import SessionLocal
from app.providers.cfbd_client import CFBDClient
from app.services.ncaaf_historical_results_import_service import (
    NCAAFHistoricalResultsImportService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import factual NCAAF history from CFBD")
    season_group = parser.add_mutually_exclusive_group(required=True)
    season_group.add_argument("--season", type=int)
    season_group.add_argument("--start-season", type=int)
    parser.add_argument("--end-season", type=int)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true")
    mode_group.add_argument("--apply", action="store_true")
    return parser


def seasons_from_args(args: argparse.Namespace) -> list[int]:
    if args.season is not None:
        if args.end_season is not None:
            raise ValueError("--end-season cannot be combined with --season")
        return [args.season]
    end_season = args.end_season if args.end_season is not None else args.start_season
    if end_season < args.start_season:
        raise ValueError("--end-season must be greater than or equal to --start-season")
    return list(range(args.start_season, end_season + 1))


def main() -> int:
    args = build_parser().parse_args()
    try:
        seasons = seasons_from_args(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    db = SessionLocal()
    try:
        report = NCAAFHistoricalResultsImportService(db, CFBDClient()).import_seasons(
            seasons,
            dry_run=not args.apply,
        )
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())