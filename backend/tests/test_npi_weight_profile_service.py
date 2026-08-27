import pytest

from app.services.npi_weight_profile_service import NPIWeightProfileService


def test_valid_profile_totals_200():

    service = NPIWeightProfileService()
    profile = {
        "home_advantage": 20,
        "spread_value": 35,
        "market_environment": 25,
        "situational_edge": 40,
        "historical_rules": 80,
    }

    service.validate_profile(profile)


def test_invalid_profile_rejected():

    service = NPIWeightProfileService()
    profile = {
        "home_advantage": 20,
        "spread_value": 30,
        "market_environment": 20,
        "situational_edge": 30,
        "historical_rules": 50,
    }

    with pytest.raises(ValueError):
        service.validate_profile(profile)


def test_missing_factor_rejected():

    service = NPIWeightProfileService()
    profile = {
        "home_advantage": 20,
        "spread_value": 35,
    }

    with pytest.raises(ValueError):
        service.validate_profile(profile)
