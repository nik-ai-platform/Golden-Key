import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.game_provider_identity import GameProviderIdentity
from app.models.game_result_observation import GameResultObservation
from app.models.import_run import ImportRun
from app.models.team import Team
from app.models.team_provider_identity import TeamProviderIdentity
from app.models.team_season import TeamSeason
from app.providers.cfbd_dtos import CFBDGame, CFBDTeam, CFBDTeamSeason
from app.services.team_identity_service import TeamIdentityService


CFBD_PROVIDER = "cfbd"
ODDS_API_PROVIDER = "the_odds_api"
SPORT = "NCAAF"
RESULT_AVAILABILITY_DELAY = timedelta(hours=6)
GAME_RECONCILIATION_WINDOW = timedelta(hours=6)


@dataclass
class HistoricalImportReport:
    seasons: tuple[int, ...]
    dry_run: bool
    rows_fetched: int = 0
    provider_teams_fetched: int = 0
    provider_metadata_fetched: int = 0
    provider_games_fetched: int = 0
    relevant_games: int = 0
    excluded_games: int = 0
    game_only_teams_proposed: int = 0
    teams_created: int = 0
    teams_matched: int = 0
    identities_created: int = 0
    aliases_created: int = 0
    team_seasons_created: int = 0
    team_seasons_updated: int = 0
    games_created: int = 0
    games_matched: int = 0
    games_updated: int = 0
    observations_created: int = 0
    provider_timestamp_observations: int = 0
    fallback_timestamp_observations: int = 0
    odds_api_identities_backfilled: int = 0
    ambiguous_records: int = 0
    ambiguous_teams: int = 0
    ambiguous_games: int = 0
    errors_count: int = 0
    match_method_counts: dict[str, int] = field(default_factory=dict)
    reviewed_alias_matches: list[str] = field(default_factory=list)
    excluded_game_classifications: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class NCAAFHistoricalResultsImportService:
    def __init__(self, db: Session, client):
        self.db = db
        self.client = client
        self.identity_service = TeamIdentityService(db)

    def import_seasons(
        self,
        seasons: list[int] | tuple[int, ...],
        *,
        dry_run: bool = True,
    ) -> HistoricalImportReport:
        normalized_seasons = tuple(sorted(set(seasons)))
        if not normalized_seasons:
            raise ValueError("At least one season is required")

        report = HistoricalImportReport(normalized_seasons, dry_run)
        transaction = self.db.begin_nested()
        started_at = _utc_now()
        import_run = ImportRun(
            provider=CFBD_PROVIDER,
            import_type="ncaaf_history",
            season_start=normalized_seasons[0],
            season_end=normalized_seasons[-1],
            dry_run=dry_run,
            status="running",
            started_at=started_at,
        )
        self.db.add(import_run)
        self.db.flush()

        try:
            report.odds_api_identities_backfilled = self._backfill_odds_api_identities()
            for season in normalized_seasons:
                self._import_season(season, import_run.id, report)
            self._validate_integrity(normalized_seasons, report)
            self._finalize_run(import_run, report, "completed")
            self.db.flush()
            if dry_run:
                transaction.rollback()
            else:
                transaction.commit()
                self.db.commit()
            return report
        except Exception as exc:
            report.errors_count += 1
            report.errors.append(str(exc))
            transaction.rollback()
            self.db.rollback()
            raise

    def _import_season(
        self,
        season: int,
        import_run_id: int,
        report: HistoricalImportReport,
    ) -> None:
        teams: list[CFBDTeam] = self.client.get_teams(season)
        metadata: list[CFBDTeamSeason] = self.client.get_team_metadata(season)
        games: list[CFBDGame] = self.client.get_games(season)
        report.provider_teams_fetched += len(teams)
        report.provider_metadata_fetched += len(metadata)
        report.provider_games_fetched += len(games)
        report.rows_fetched += len(teams) + len(metadata) + len(games)

        metadata_by_id = {item.team_id: item for item in metadata}
        teams_by_id = {team.id: team for team in teams}
        for item in metadata:
            teams_by_id.setdefault(
                item.team_id,
                CFBDTeam(id=item.team_id, school=item.school),
            )

        conflicting_game_team_ids: set[int] = set()
        for game in games:
            for provider_team_id, provider_name in (
                (game.home_id, game.home_team),
                (game.away_id, game.away_team),
            ):
                if not provider_team_id or not provider_name.strip():
                    conflicting_game_team_ids.add(provider_team_id)
                    continue
                existing = teams_by_id.get(provider_team_id)
                if existing is None:
                    teams_by_id[provider_team_id] = CFBDTeam(
                        id=provider_team_id,
                        school=provider_name.strip(),
                        metadata_complete=False,
                    )
                    report.game_only_teams_proposed += 1
                elif (
                    not existing.metadata_complete
                    and self.identity_service.normalize_name(existing.school)
                    != self.identity_service.normalize_name(provider_name)
                ):
                    conflicting_game_team_ids.add(provider_team_id)

        for provider_team_id in conflicting_game_team_ids:
            source_team = teams_by_id.get(provider_team_id)
            if source_team is not None and not source_team.metadata_complete:
                teams_by_id.pop(provider_team_id)
            report.warnings.append(
                f"Season {season}: conflicting or incomplete game-only team "
                f"{provider_team_id}"
            )

        relevant_games: list[CFBDGame] = []
        relevant_team_ids = {
            item.team_id for item in metadata if self._is_primary_classification(item)
        }
        excluded_counts: Counter[str] = Counter()
        for game in games:
            home_class = self._classification_label(metadata_by_id.get(game.home_id))
            away_class = self._classification_label(metadata_by_id.get(game.away_id))
            if home_class in {"FBS", "FCS"} or away_class in {"FBS", "FCS"}:
                relevant_games.append(game)
                relevant_team_ids.update((game.home_id, game.away_id))
            else:
                combination = " vs ".join(sorted((home_class, away_class)))
                excluded_counts[combination] += 1
        report.relevant_games += len(relevant_games)
        report.excluded_games += len(games) - len(relevant_games)
        self._merge_counts(report.excluded_game_classifications, excluded_counts)

        normalized_counts = Counter(
            self.identity_service.normalize_name(team.school)
            for provider_team_id, team in teams_by_id.items()
            if provider_team_id in relevant_team_ids
        )
        canonical_team_ids: dict[int, int] = {}
        candidate_team_ids = {
            team_id
            for (team_id,) in self.db.query(Team.id).filter(Team.sport == SPORT).all()
        }
        observed_at = _utc_now()
        for provider_team_id, source_team in teams_by_id.items():
            if provider_team_id not in relevant_team_ids:
                continue
            normalized_name = self.identity_service.normalize_name(source_team.school)
            existing_identity = self._find_team_identity(provider_team_id)
            allow_create = normalized_counts[normalized_name] == 1
            resolution = self.identity_service.resolve(
                provider=CFBD_PROVIDER,
                provider_team_id=str(provider_team_id),
                provider_name=source_team.school,
                sport=SPORT,
                league=SPORT,
                provider_aliases=source_team.alternate_names,
                candidate_team_ids=candidate_team_ids,
                allow_create=allow_create,
                observed_at=observed_at,
            )
            if resolution.team is None:
                report.ambiguous_records += 1
                report.ambiguous_teams += 1
                report.warnings.append(
                    f"Season {season}: unresolved team {provider_team_id} "
                    f"({source_team.school}); method={resolution.method}"
                )
                continue

            canonical_team_ids[provider_team_id] = resolution.team.id
            report.match_method_counts[resolution.method] = (
                report.match_method_counts.get(resolution.method, 0) + 1
            )
            if resolution.method in {"reviewed_alias", "reviewed_provider_mapping"}:
                report.reviewed_alias_matches.append(
                    f"{provider_team_id}: {resolution.provider_name} -> "
                    f"{resolution.canonical_name}"
                )
            if resolution.method == "new_team":
                report.teams_created += 1
            else:
                report.teams_matched += 1
            if existing_identity is None:
                report.identities_created += 1

            aliases = self._deduplicate_aliases(
                source_team.school,
                source_team.abbreviation,
                *source_team.alternate_names,
            )
            for alias in aliases:
                if self.identity_service.add_alias(
                    team_id=resolution.team.id,
                    provider=CFBD_PROVIDER,
                    alias_name=alias,
                ):
                    report.aliases_created += 1

            season_metadata = metadata_by_id.get(provider_team_id)
            if season_metadata is not None:
                self._upsert_team_season(
                    resolution.team.id,
                    season,
                    season_metadata,
                    observed_at,
                    report,
                )

        self.db.flush()
        for source_game in relevant_games:
            self._import_game(
                source_game,
                canonical_team_ids,
                import_run_id,
                report,
            )

    @staticmethod
    def _is_primary_classification(metadata: CFBDTeamSeason) -> bool:
        return NCAAFHistoricalResultsImportService._classification_label(metadata) in {
            "FBS",
            "FCS",
        }

    @staticmethod
    def _classification_label(metadata: CFBDTeamSeason | None) -> str:
        if metadata is None:
            return "Unknown"
        if metadata.is_fbs is True:
            return "FBS"
        classification = (metadata.classification or "").strip().upper()
        if classification in {"FBS", "FCS"}:
            return classification
        return classification or "Unknown"

    @staticmethod
    def _merge_counts(target: dict[str, int], source: Counter[str]) -> None:
        for key, value in source.items():
            target[key] = target.get(key, 0) + value

    def _deduplicate_aliases(self, *aliases: str | None) -> tuple[str, ...]:
        unique: dict[str, str] = {}
        for alias in aliases:
            if not alias:
                continue
            normalized = self.identity_service.normalize_name(alias)
            if normalized:
                unique.setdefault(normalized, alias)
        return tuple(unique.values())

    def _find_team_identity(self, provider_team_id: int) -> TeamProviderIdentity | None:
        return (
            self.db.query(TeamProviderIdentity)
            .filter(
                TeamProviderIdentity.provider == CFBD_PROVIDER,
                TeamProviderIdentity.sport == SPORT,
                TeamProviderIdentity.provider_team_id == str(provider_team_id),
            )
            .one_or_none()
        )

    def _upsert_team_season(
        self,
        team_id: int,
        season: int,
        metadata: CFBDTeamSeason,
        observed_at: datetime,
        report: HistoricalImportReport,
    ) -> None:
        row = (
            self.db.query(TeamSeason)
            .filter(
                TeamSeason.team_id == team_id,
                TeamSeason.season == season,
                TeamSeason.source_provider == CFBD_PROVIDER,
            )
            .one_or_none()
        )
        values = {
            "conference_name": metadata.conference,
            "classification": metadata.classification,
            "division": metadata.division,
            "is_fbs": metadata.is_fbs,
        }
        if row is None:
            self.db.add(
                TeamSeason(
                    team_id=team_id,
                    season=season,
                    source_provider=CFBD_PROVIDER,
                    observed_at=observed_at,
                    **values,
                )
            )
            report.team_seasons_created += 1
            return

        changed = any(getattr(row, name) != value for name, value in values.items())
        if changed:
            for name, value in values.items():
                setattr(row, name, value)
            row.observed_at = observed_at
            report.team_seasons_updated += 1

    def _import_game(
        self,
        source_game: CFBDGame,
        canonical_team_ids: dict[int, int],
        import_run_id: int,
        report: HistoricalImportReport,
    ) -> None:
        home_team_id = canonical_team_ids.get(source_game.home_id)
        away_team_id = canonical_team_ids.get(source_game.away_id)
        if home_team_id is None or away_team_id is None or home_team_id == away_team_id:
            report.ambiguous_records += 1
            report.ambiguous_games += 1
            report.warnings.append(
                f"Game {source_game.id}: unresolved or identical canonical teams"
            )
            return

        game_identity = (
            self.db.query(GameProviderIdentity)
            .filter(
                GameProviderIdentity.provider == CFBD_PROVIDER,
                GameProviderIdentity.provider_game_id == str(source_game.id),
            )
            .one_or_none()
        )
        game = self.db.get(Game, game_identity.game_id) if game_identity else None
        created = False
        if game is None:
            matches = self._find_reconciliation_matches(
                source_game,
                home_team_id,
                away_team_id,
            )
            if len(matches) > 1:
                report.ambiguous_records += 1
                report.ambiguous_games += 1
                report.warnings.append(
                    f"Game {source_game.id}: {len(matches)} reconciliation candidates"
                )
                return
            game = matches[0] if matches else None
        if game is None:
            winner_team_id = None
            if source_game.home_points is not None and source_game.away_points is not None:
                if source_game.home_points > source_game.away_points:
                    winner_team_id = home_team_id
                elif source_game.away_points > source_game.home_points:
                    winner_team_id = away_team_id
            game = Game(
                sport=SPORT,
                league=SPORT,
                season=source_game.season,
                provider_game_id=None,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                game_date=source_game.start_date,
                home_score=source_game.home_points if source_game.completed else None,
                away_score=source_game.away_points if source_game.completed else None,
                winner_team_id=winner_team_id if source_game.completed else None,
                status="final" if source_game.completed else "scheduled",
                neutral_site=source_game.neutral_site,
                venue_name=source_game.venue_name,
                venue_city=source_game.venue_city,
                venue_state=source_game.venue_state,
            )
            self.db.add(game)
            self.db.flush()
            report.games_created += 1
            created = True
        else:
            report.games_matched += 1

        if game_identity is None:
            self.db.add(
                GameProviderIdentity(
                    game_id=game.id,
                    provider=CFBD_PROVIDER,
                    provider_game_id=str(source_game.id),
                )
            )

        metadata_changed = False
        for field_name in ("neutral_site", "venue_name", "venue_city", "venue_state"):
            source_value = getattr(source_game, field_name)
            if source_value is not None and getattr(game, field_name) != source_value:
                setattr(game, field_name, source_value)
                metadata_changed = True
        if metadata_changed and not created:
            report.games_updated += 1

        if (
            source_game.completed
            and source_game.home_points is not None
            and source_game.away_points is not None
        ):
            self._append_result_observation(
                game,
                source_game,
                import_run_id,
                report,
            )

    def _find_reconciliation_matches(
        self,
        source_game: CFBDGame,
        home_team_id: int,
        away_team_id: int,
    ) -> list[Game]:
        window_start = source_game.start_date - GAME_RECONCILIATION_WINDOW
        window_end = source_game.start_date + GAME_RECONCILIATION_WINDOW
        return (
            self.db.query(Game)
            .filter(
                Game.sport == SPORT,
                Game.season == source_game.season,
                Game.home_team_id == home_team_id,
                Game.away_team_id == away_team_id,
                Game.game_date >= window_start,
                Game.game_date <= window_end,
            )
            .all()
        )

    def _append_result_observation(
        self,
        game: Game,
        source_game: CFBDGame,
        import_run_id: int,
        report: HistoricalImportReport,
    ) -> None:
        observed_at = source_game.source_updated_at or (
            source_game.start_date + RESULT_AVAILABILITY_DELAY
        )
        if source_game.source_updated_at is None:
            report.fallback_timestamp_observations += 1
        else:
            report.provider_timestamp_observations += 1
        payload = {
            "provider_game_id": source_game.id,
            "home_points": source_game.home_points,
            "away_points": source_game.away_points,
            "completed": source_game.completed,
            "source_updated_at": (
                source_game.source_updated_at.isoformat()
                if source_game.source_updated_at
                else None
            ),
        }
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        existing = (
            self.db.query(GameResultObservation)
            .filter(
                GameResultObservation.game_id == game.id,
                GameResultObservation.provider == CFBD_PROVIDER,
                GameResultObservation.payload_hash == payload_hash,
            )
            .one_or_none()
        )
        if existing is None:
            self.db.add(
                GameResultObservation(
                    game_id=game.id,
                    provider=CFBD_PROVIDER,
                    home_score=source_game.home_points,
                    away_score=source_game.away_points,
                    status="final",
                    observed_at=observed_at,
                    source_updated_at=source_game.source_updated_at,
                    payload_hash=payload_hash,
                    import_run_id=import_run_id,
                )
            )
            report.observations_created += 1

        if (
            game.historical_result_observed_at is None
            or observed_at < game.historical_result_observed_at
        ):
            game.historical_result_observed_at = observed_at

    def _backfill_odds_api_identities(self) -> int:
        created = 0
        games = (
            self.db.query(Game)
            .filter(Game.sport == SPORT, Game.provider_game_id.isnot(None))
            .all()
        )
        for game in games:
            exists = (
                self.db.query(GameProviderIdentity.id)
                .filter(
                    GameProviderIdentity.provider == ODDS_API_PROVIDER,
                    GameProviderIdentity.provider_game_id == game.provider_game_id,
                )
                .first()
            )
            if exists is None:
                self.db.add(
                    GameProviderIdentity(
                        game_id=game.id,
                        provider=ODDS_API_PROVIDER,
                        provider_game_id=game.provider_game_id,
                    )
                )
                created += 1
        self.db.flush()
        return created

    def _validate_integrity(
        self,
        seasons: tuple[int, ...],
        report: HistoricalImportReport,
    ) -> None:
        invalid_games = (
            self.db.query(Game.id)
            .filter(
                Game.sport == SPORT,
                Game.season.in_(seasons),
                Game.home_team_id == Game.away_team_id,
            )
            .count()
        )
        if invalid_games:
            raise ValueError(f"Integrity check failed: {invalid_games} games use one team twice")
        if report.ambiguous_records:
            report.warnings.append(
                f"Quarantined {report.ambiguous_records} ambiguous or unresolved records"
            )

    @staticmethod
    def _finalize_run(
        import_run: ImportRun,
        report: HistoricalImportReport,
        status: str,
    ) -> None:
        import_run.status = status
        import_run.completed_at = _utc_now()
        import_run.rows_fetched = report.rows_fetched
        import_run.teams_created = report.teams_created
        import_run.teams_matched = report.teams_matched
        import_run.aliases_created = report.aliases_created
        import_run.games_created = report.games_created
        import_run.games_matched = report.games_matched
        import_run.games_updated = report.games_updated
        import_run.ambiguous_records = report.ambiguous_records
        import_run.errors_count = report.errors_count
        import_run.checkpoint = json.dumps(
            {"seasons": report.seasons, "warnings": report.warnings},
            sort_keys=True,
        )
        import_run.source_schema_version = "cfbd-v2"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)