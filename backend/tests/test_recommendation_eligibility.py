import pytest

from app.services.recommendation_eligibility import (
    LOWER_PRIORITY,
    LOW_VALUE_DESIGNATION,
    LOW_VALUE_HEAVY_FAVORITE,
    PREFERRED,
    is_recommendation_eligible,
    moneyline_price_tier,
    recommendation_designation,
)


@pytest.mark.parametrize(
    ("market", "odds", "eligible", "tier", "designation"),
    (
        ("spread", None, True, None, None),
        ("total", None, True, None, None),
        ("moneyline", None, False, None, None),
        ("moneyline", -400, True, LOWER_PRIORITY, None),
        ("moneyline", -301, True, LOWER_PRIORITY, None),
        ("moneyline", -300, True, PREFERRED, None),
        ("moneyline", 300, True, PREFERRED, None),
        ("moneyline", 301, True, None, None),
        (
            "moneyline",
            -401,
            False,
            LOW_VALUE_HEAVY_FAVORITE,
            LOW_VALUE_DESIGNATION,
        ),
        (
            "moneyline",
            -20000,
            False,
            LOW_VALUE_HEAVY_FAVORITE,
            LOW_VALUE_DESIGNATION,
        ),
    ),
)
def test_recommendation_policy_boundaries(
    market,
    odds,
    eligible,
    tier,
    designation,
):
    assert is_recommendation_eligible(market, odds) is eligible
    assert moneyline_price_tier(market, odds) == tier
    assert recommendation_designation(market, odds) == designation