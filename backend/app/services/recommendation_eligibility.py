PREFERRED = "PREFERRED"
LOWER_PRIORITY = "LOWER_PRIORITY"
LOW_VALUE_HEAVY_FAVORITE = "LOW_VALUE_HEAVY_FAVORITE"
LOW_VALUE_DESIGNATION = "High Probability — Low Betting Value"


def moneyline_price_tier(
    market: str | None,
    american_odds: int | float | None,
) -> str | None:
    if (market or "").lower() != "moneyline" or american_odds is None:
        return None

    odds = float(american_odds)
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
    if (market or "").lower() != "moneyline":
        return True
    if american_odds is None:
        return False
    return float(american_odds) >= -400


def recommendation_designation(
    market: str | None,
    american_odds: int | float | None,
) -> str | None:
    if moneyline_price_tier(market, american_odds) == LOW_VALUE_HEAVY_FAVORITE:
        return LOW_VALUE_DESIGNATION
    return None