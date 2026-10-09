from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from app.services.live_data_service import LiveDataService
from app.services.monitoring_service import MonitoringService
from app.services.odds_service import create_odds_snapshot
from app.models.team import Team
from app.models.game import Game
from app.services.sport_mapping_service import CompetitionSource, SportMappingService
from app.services.odds_provider_client import safe_sync_error


logger = logging.getLogger(__name__)


@dataclass
class SourceImportSummary:
    provider_source: str
    league: str
    fetched: int = 0
    processed: int = 0
    created: int = 0
    refreshed: int = 0
    usable_odds: int = 0
    skipped_no_odds: int = 0
    predictions: int = 0
    predictions_skipped_no_odds: int = 0
    errors: int = 0
    game_date_min: datetime | None = None
    game_date_max: datetime | None = None
    game_ids: list[int] = field(default_factory=list)
    price_capture_diagnostics: dict[str, int] = field(default_factory=dict)


class GameOddsImporter:

    def __init__(
        self,
        db: Session,
        live_data_service=None,
        monitor=None,
    ):
        self.db = db
        self.live_data = (
            live_data_service or LiveDataService()
        )
        self.monitor = monitor or MonitoringService()
        self.sport_mapping = SportMappingService()
        self.source_imports: list[SourceImportSummary] = []

    def import_games(
        self,
        sport: str
    ):

        sport = sport.strip().upper()

        imported = []
        self.source_imports = []
        for source in self.sport_mapping.competition_sources(sport):
            summary = SourceImportSummary(source.provider_key, source.league)
            self.source_imports.append(summary)
            try:
                games = self.live_data.fetch_games(
                    source.provider_key if sport == "NBA" else sport
                )
                if not isinstance(games, list):
                    raise ValueError("Unexpected odds provider response")
                summary.fetched = len(games)
            except Exception as exc:
                self.db.rollback()
                summary.errors += 1
                # Request exceptions can contain a credential-bearing URL.
                logger.error(
                    "Game source fetch failed sport=%s provider_source=%s error_type=%s",
                    sport, source.provider_key, type(exc).__name__,
                )
                if sport != "NBA":
                    raise safe_sync_error(exc, source.provider_key) from None
                continue

            for game_data in games:
                try:
                    game, created = self._upsert_game(sport, source, game_data)
                    summary.created += int(created)
                    summary.refreshed += int(not created)
                    usable_odds = self.import_odds(
                        game,
                        game_data,
                        price_capture_diagnostics=summary.price_capture_diagnostics,
                    )
                    summary.processed += 1
                    summary.usable_odds += int(usable_odds > 0)
                    summary.skipped_no_odds += int(usable_odds == 0)
                    summary.game_ids.append(game.id)
                    summary.game_date_min = min(
                        summary.game_date_min or game.game_date, game.game_date,
                    )
                    summary.game_date_max = max(
                        summary.game_date_max or game.game_date, game.game_date,
                    )
                    imported.append(game)
                except Exception as exc:
                    self.db.rollback()
                    summary.errors += 1
                    logger.error(
                        "Game source import failed sport=%s provider_source=%s "
                        "provider_event_id=%s error_type=%s",
                        sport, source.provider_key,
                        game_data.get("id") if isinstance(game_data, dict) else None,
                        type(exc).__name__,
                    )
                    if sport != "NBA":
                        raise safe_sync_error(exc, source.provider_key) from None

        if sport == "NBA" and not imported and all(
            summary.errors > 0 for summary in self.source_imports
        ):
            raise RuntimeError("All NBA competition sources failed") from None

        self.monitor.log_import(
            "Imported games",
            count=len(imported),
            sport=sport
        )

        return imported

    def _upsert_game(
        self, sport: str, source: CompetitionSource, game_data: dict,
    ) -> tuple[Game, bool]:
        provider_game_id = game_data.get("id")
        if not provider_game_id:
            raise ValueError("Provider game is missing an id")
        game_date = self._parse_game_time(game_data["commence_time"])
        game = (
            self.db.query(Game)
            .filter(Game.provider_game_id == provider_game_id)
            .first()
        )
        if game and sport == "NBA" and (
            game.sport != sport or game.league != source.league
        ):
            logger.error(
                "Game identity conflict provider_source=%s provider_event_id=%s "
                "stored_sport=%s stored_league=%s incoming_sport=%s incoming_league=%s",
                source.provider_key, provider_game_id, game.sport, game.league,
                sport, source.league,
            )
            raise ValueError("Provider event identity conflicts with stored competition")

        home_team = self.get_or_create_team(game_data["home_team"], sport)
        away_team = self.get_or_create_team(game_data["away_team"], sport)
        created = game is None
        if game:
            if sport != "NBA":
                game.sport = sport
                game.league = sport
            game.game_date = game_date
            game.home_team_id = home_team.id
            game.away_team_id = away_team.id
        else:
            game = Game(
                provider_game_id=provider_game_id,
                sport=sport,
                league=source.league,
                season=game_date.year,
                game_date=game_date,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
            )
            self.db.add(game)
        neutral_site = self._provider_neutral_site(game_data)
        if neutral_site is not None:
            game.neutral_site = neutral_site
        for field_name in ("venue_name", "venue_city", "venue_state"):
            value = game_data.get(field_name)
            if isinstance(value, str) and value.strip():
                setattr(game, field_name, value.strip())
        self.db.commit()
        self.db.refresh(game)
        return game, created

    def get_or_create_team(
        self,
        name,
        sport
    ):

        team = (
            self.db.query(Team)
            .filter(
                Team.name == name,
                Team.sport == sport,
            )
            .first()
        )

        if team:
            return team

        team = Team(
            name=name,
            sport=sport,
            league=sport
        )

        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)

        return team

    @staticmethod
    def _provider_neutral_site(game_data: dict) -> bool | None:
        for key in ("neutral_site", "neutralSite"):
            value = game_data.get(key)
            if isinstance(value, bool):
                return value
        return None

    def import_odds(
        self,
        game,
        game_data,
        *,
        price_capture_diagnostics: dict[str, int] | None = None,
    ):

        imported_count = 0
        for bookmaker in game_data.get(
            "bookmakers",
            []
        ):
            odds = create_odds_snapshot(
                self.db,
                game.id,
                bookmaker,
                price_capture_diagnostics=price_capture_diagnostics,
            )
            if odds is not None:
                imported_count += 1

        self.db.commit()

        self.monitor.log_import(
            "Imported odds",
            game_id=game.id,
            count=imported_count,
        )
        return imported_count

    def _parse_game_time(
        self,
        commence_time: str
    ) -> datetime:
        parsed = datetime.fromisoformat(
            commence_time.replace("Z", "+00:00")
        )
        return (
            parsed.astimezone(timezone.utc).replace(tzinfo=None)
            if parsed.tzinfo is not None else parsed
        )
