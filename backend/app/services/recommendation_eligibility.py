PREFERRED = "PREFERRED"
LOWER_PRIORITY = "LOWER_PRIORITY"
LOW_VALUE_HEAVY_FAVORITE = "LOW_VALUE_HEAVY_FAVORITE"
LOW_VALUE_DESIGNATION = "High Probability — Low Betting Value"


def moneyline_price_tier(
    market: str | None,
    american_odds: int | float | None,
) -> str | None:
    odds = historical_price(american_odds)
    if parse_market(market) != "moneyline" or odds is None:
        return None

    if odds < -400:
        return LOW_VALUE_HEAVY_FAVORITE
    if odds < -300:
        return LOWER_PRIORITY
    if odds <= 300:
        return PREFERRED
    return None


def is_recommendation_eligible(
    market: str | None,
    american_odds: int | float | None,
) -> bool:
    parsed_market = parse_market(market)
    if parsed_market != "moneyline":
        return parsed_market is not None
    odds = historical_price(american_odds)
    if odds is None:
        return False
    return odds >= -400


def recommendation_designation(
    market: str | None,
    american_odds: int | float | None,
) -> str | None:
    if moneyline_price_tier(market, american_odds) == LOW_VALUE_HEAVY_FAVORITE:
        return LOW_VALUE_DESIGNATION
    return None
from app.services.prediction_metric_contract import historical_price, parse_market
