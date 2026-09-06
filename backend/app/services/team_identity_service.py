import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.data.ncaaf_team_aliases import (
    REVIEWED_CFBD_TEAM_MAPPINGS,
    REVIEWED_NCAAF_TEAM_ALIASES,
)
from app.models.team import Team
from app.models.team_alias import TeamAlias
from app.models.team_provider_identity import TeamProviderIdentity


@dataclass(frozen=True)
class TeamResolution:
    team: Team | None
    method: str
    ambiguous_team_ids: tuple[int, ...] = ()
    provider_name: str | None = None
    canonical_name: str | None = None

    @property
    def is_ambiguous(self) -> bool:
        return bool(self.ambiguous_team_ids)


class TeamIdentityService:
    MIN_PREFIX_LENGTH = 5
    DIRECTIONAL_ONLY_NAMES = {"eastern", "northern", "southern", "western"}
    INSTITUTIONAL_SUFFIXES = (
        "state",
        "tech",
        "university",
        "college",
        "am",
    )

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def normalize_name(name: str) -> str:
        ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", "", ascii_name.lower())

    def resolve(
        self,
        *,
        provider: str,
        provider_team_id: str,
        provider_name: str,
        sport: str,
        league: str,
        provider_aliases: tuple[str, ...] = (),
        candidate_team_ids: set[int] | None = None,
        allow_create: bool = True,
        observed_at: datetime | None = None,
    ) -> TeamResolution:
        observed_at = observed_at or datetime.now(timezone.utc).replace(tzinfo=None)
        identity = (
            self.db.query(TeamProviderIdentity)
            .filter(
                TeamProviderIdentity.provider == provider,
                TeamProviderIdentity.sport == sport,
                TeamProviderIdentity.provider_team_id == str(provider_team_id),
            )
            .one_or_none()
        )
        if identity is not None:
            identity.provider_name = provider_name
            identity.last_seen_at = observed_at
            team = self.db.get(Team, identity.team_id)
            return TeamResolution(
                team,
                "provider_identity",
                provider_name=provider_name,
                canonical_name=team.name,
            )

        sport_teams_query = self.db.query(Team).filter(Team.sport == sport)
        if candidate_team_ids is not None:
            sport_teams_query = sport_teams_query.filter(Team.id.in_(candidate_team_ids))
        sport_teams = sport_teams_query.all()
        reviewed_target = (
            REVIEWED_CFBD_TEAM_MAPPINGS.get(str(provider_team_id))
            if provider == "cfbd"
            else None
        )
        if reviewed_target is not None:
            reviewed_matches = [
                team
                for team in sport_teams
                if self.normalize_name(team.name)
                == self.normalize_name(reviewed_target)
            ]
            if len(reviewed_matches) == 1:
                team = reviewed_matches[0]
                self._add_identity(
                    team.id,
                    provider,
                    sport,
                    str(provider_team_id),
                    provider_name,
                    observed_at,
                )
                return TeamResolution(
                    team,
                    "reviewed_provider_mapping",
                    provider_name=provider_name,
                    canonical_name=team.name,
                )
            return TeamResolution(
                None,
                "unresolved",
                tuple(sorted(team.id for team in reviewed_matches)),
                provider_name=provider_name,
            )

        normalized_name = self.normalize_name(provider_name)
        normalized_provider_names = {
            self.normalize_name(name)
            for name in (provider_name, *provider_aliases)
            if name
        }
        aliases = (
            self.db.query(TeamAlias)
            .join(Team, Team.id == TeamAlias.team_id)
            .filter(
                TeamAlias.provider == provider,
                TeamAlias.normalized_alias.in_(normalized_provider_names),
                Team.sport == sport,
            )
        )
        if candidate_team_ids is not None:
            aliases = aliases.filter(Team.id.in_(candidate_team_ids))
        aliases = aliases.all()
        alias_team_ids = sorted({alias.team_id for alias in aliases})
        if len(alias_team_ids) == 1:
            team = self.db.get(Team, alias_team_ids[0])
            self._add_identity(
                team.id, provider, sport, str(provider_team_id), provider_name, observed_at
            )
            return TeamResolution(
                team,
                "exact_alias",
                provider_name=provider_name,
                canonical_name=team.name,
            )
        if len(alias_team_ids) > 1:
            return TeamResolution(
                None,
                "unresolved",
                tuple(alias_team_ids),
                provider_name=provider_name,
            )

        canonical_matches = [
            team
            for team in sport_teams
            if self.normalize_name(team.name) in normalized_provider_names
        ]
        if len(canonical_matches) == 1:
            team = canonical_matches[0]
            self._add_identity(
                team.id, provider, sport, str(provider_team_id), provider_name, observed_at
            )
            return TeamResolution(
                team,
                "exact_canonical",
                provider_name=provider_name,
                canonical_name=team.name,
            )
        if len(canonical_matches) > 1:
            return TeamResolution(
                None,
                "unresolved",
                tuple(sorted(team.id for team in canonical_matches)),
                provider_name=provider_name,
            )

        prefix_matches = self._mascot_suffix_matches(
            provider_name,
            provider_aliases,
            sport_teams,
        )
        if len(prefix_matches) == 1:
            team = prefix_matches[0]
            self._add_identity(
                team.id, provider, sport, str(provider_team_id), provider_name, observed_at
            )
            return TeamResolution(
                team,
                "mascot_suffix",
                provider_name=provider_name,
                canonical_name=team.name,
            )
        if len(prefix_matches) > 1:
            return TeamResolution(
                None,
                "unresolved",
                tuple(sorted(team.id for team in prefix_matches)),
                provider_name=provider_name,
            )

        reviewed_target = REVIEWED_NCAAF_TEAM_ALIASES.get(normalized_name)
        if reviewed_target is not None:
            reviewed_matches = self._target_prefix_matches(reviewed_target, sport_teams)
            if len(reviewed_matches) == 1:
                team = reviewed_matches[0]
                self._add_identity(
                    team.id,
                    provider,
                    sport,
                    str(provider_team_id),
                    provider_name,
                    observed_at,
                )
                return TeamResolution(
                    team,
                    "reviewed_alias",
                    provider_name=provider_name,
                    canonical_name=team.name,
                )
            if len(reviewed_matches) > 1:
                return TeamResolution(
                    None,
                    "unresolved",
                    tuple(sorted(team.id for team in reviewed_matches)),
                    provider_name=provider_name,
                )
        if not allow_create:
            return TeamResolution(None, "unresolved", provider_name=provider_name)

        team = Team(name=provider_name, league=league, sport=sport)
        self.db.add(team)
        self.db.flush()
        self._add_identity(
            team.id, provider, sport, str(provider_team_id), provider_name, observed_at
        )
        return TeamResolution(
            team,
            "new_team",
            provider_name=provider_name,
            canonical_name=team.name,
        )

    def _mascot_suffix_matches(
        self,
        provider_name: str,
        provider_aliases: tuple[str, ...],
        teams: list[Team],
    ) -> list[Team]:
        source_names = (provider_name, *provider_aliases)
        normalized_sources = {
            self.normalize_name(name)
            for name in source_names
            if self._is_meaningful_prefix(name)
        }
        matches: dict[int, Team] = {}
        competing_matches: dict[int, Team] = {}
        for source in normalized_sources:
            for team in teams:
                canonical = self.normalize_name(team.name)
                if self._is_mascot_suffix(source, canonical):
                    matches[team.id] = team
                elif self._is_institutional_continuation(source, canonical):
                    competing_matches[team.id] = team
        if matches and competing_matches:
            matches.update(competing_matches)
        return list(matches.values())

    def _target_prefix_matches(self, target: str, teams: list[Team]) -> list[Team]:
        return [
            team
            for team in teams
            if self._is_mascot_suffix(target, self.normalize_name(team.name))
        ]

    def _is_meaningful_prefix(self, name: str) -> bool:
        normalized = self.normalize_name(name)
        return (
            normalized not in self.DIRECTIONAL_ONLY_NAMES
            and len(normalized) >= self.MIN_PREFIX_LENGTH
            and not (
            name.isupper() and len(normalized) <= 5
            )
        )

    def _is_mascot_suffix(self, source: str, canonical: str) -> bool:
        if not canonical.startswith(source) or canonical == source:
            return False
        remainder = canonical[len(source):]
        return not any(remainder.startswith(token) for token in self.INSTITUTIONAL_SUFFIXES)

    def _is_institutional_continuation(self, source: str, canonical: str) -> bool:
        if not canonical.startswith(source) or canonical == source:
            return False
        remainder = canonical[len(source):]
        return any(remainder.startswith(token) for token in self.INSTITUTIONAL_SUFFIXES)

    def add_alias(
        self,
        *,
        team_id: int,
        provider: str,
        alias_name: str,
        confidence: float = 1.0,
        review_state: str = "provider_asserted",
    ) -> bool:
        normalized_alias = self.normalize_name(alias_name)
        if not normalized_alias:
            return False
        alias_key = (team_id, provider, normalized_alias)
        if any(
            isinstance(row, TeamAlias)
            and (row.team_id, row.provider, row.normalized_alias) == alias_key
            for row in self.db.new
        ):
            return False
        with self.db.no_autoflush:
            existing = (
                self.db.query(TeamAlias)
                .filter(
                    TeamAlias.team_id == team_id,
                    TeamAlias.provider == provider,
                    TeamAlias.normalized_alias == normalized_alias,
                )
                .one_or_none()
            )
        if existing is not None:
            return False
        self.db.add(
            TeamAlias(
                team_id=team_id,
                provider=provider,
                alias_name=alias_name,
                normalized_alias=normalized_alias,
                confidence=confidence,
                review_state=review_state,
            )
        )
        return True

    def _add_identity(
        self,
        team_id: int,
        provider: str,
        sport: str,
        provider_team_id: str,
        provider_name: str,
        observed_at: datetime,
    ) -> None:
        self.db.add(
            TeamProviderIdentity(
                team_id=team_id,
                provider=provider,
                sport=sport,
                provider_team_id=provider_team_id,
                provider_name=provider_name,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
            )
        )
        self.db.flush()