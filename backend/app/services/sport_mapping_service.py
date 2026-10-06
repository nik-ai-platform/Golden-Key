from dataclasses import dataclass


NBA_PRESEASON = "NBA_PRESEASON"


@dataclass(frozen=True)
class CompetitionSource:
    provider_key: str
    league: str


class SportMappingService:

    INTERNAL_TO_PROVIDER = {
        "NFL": "americanfootball_nfl",
        "NBA": "basketball_nba",
        "NCAAF": "americanfootball_ncaaf",
        "NCAAB": "basketball_ncaab",
        "WNBA": "basketball_wnba",
    }

    def provider_key(self, sport: str) -> str:
        normalized = sport.strip()
        key = self.INTERNAL_TO_PROVIDER.get(normalized.upper())
        if not key and "_" in normalized:
            return normalized.lower()
        if not key:
            raise ValueError(f"Unsupported sport: {sport}")

        return key

    def competition_sources(self, sport: str) -> tuple[CompetitionSource, ...]:
        normalized = sport.strip().upper()
        if normalized == "NBA":
            return (
                CompetitionSource(self.provider_key("NBA"), "NBA"),
                CompetitionSource("basketball_nba_preseason", NBA_PRESEASON),
            )
        return (CompetitionSource(self.provider_key(sport), normalized),)
