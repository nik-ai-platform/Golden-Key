from app.core.config import settings
from app.providers.base import SportsDataProvider
from app.providers.odds_api import OddsAPIProvider
from app.providers.sports_data_provider import MockSportsDataProvider


def get_sports_data_provider() -> SportsDataProvider:
    provider_name = settings.SPORTS_DATA_PROVIDER.lower()

    if provider_name == "mock":
        return MockSportsDataProvider()

    raise ValueError(
        f"Unsupported sports data provider: {settings.SPORTS_DATA_PROVIDER}"
    )


def get_odds_provider() -> SportsDataProvider:
    provider_name = settings.ODDS_PROVIDER.lower()

    if provider_name == "mock":
        return OddsAPIProvider()

    raise ValueError(
        f"Unsupported odds provider: {settings.ODDS_PROVIDER}"
    )
