class SportMappingService:

    INTERNAL_TO_PROVIDER = {
        "NFL": "americanfootball_nfl",
        "NBA": "basketball_nba",
        "NCAAF": "americanfootball_ncaaf",
        "NCAAB": "basketball_ncaab",
        "WNBA": "basketball_wnba",
    }

    def provider_key(self, sport: str) -> str:
        key = self.INTERNAL_TO_PROVIDER.get(sport.upper())
        if not key:
            raise ValueError(f"Unsupported sport: {sport}")

        return key
