from app.providers.factory import (
    get_odds_provider,
    get_sports_data_provider,
)


class LiveDataService:

    def fetch_games(self, sport: str):
        return get_live_odds(sport)

    def fetch_odds(self, sport: str):
        return get_live_odds(sport)

    def fetch_scores(self, sport: str):
        return get_live_scores(sport)


def get_live_games(sport: str):
    provider = get_sports_data_provider()
    return provider.get_games(sport)


def get_live_odds(sport: str):
    provider = get_odds_provider()
    return provider.get_odds(sport)


def get_live_scores(sport: str):
    provider = get_sports_data_provider()
    return provider.get_scores(sport)
