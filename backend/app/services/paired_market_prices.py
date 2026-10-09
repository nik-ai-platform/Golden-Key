"""Capture paired provider prices only for the stored, matching market lines."""

from decimal import Decimal, InvalidOperation
from typing import Any


def _number(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _price(value: Any) -> int | None:
    number = _number(value)
    if number is None or number != number.to_integral_value() or abs(number) < 100:
        return None
    return int(number)


def paired_market_prices(
    bookmaker: dict[str, Any],
    home_team: str,
    away_team: str,
    *,
    spread_home: Any,
    spread_away: Any,
    total: Any,
) -> dict[str, int | None]:
    prices: dict[str, int | None] = {
        "spread_home_price": None,
        "spread_away_price": None,
        "total_over_price": None,
        "total_under_price": None,
    }
    for market in bookmaker.get("markets", []):
        key = market.get("key")
        if key not in {"spreads", "totals"}:
            continue
        names = (home_team, away_team) if key == "spreads" else ("Over", "Under")
        # Ambiguous duplicate outcomes must not be paired across alternate lines.
        sides = [[o for o in market.get("outcomes", []) if o.get("name") == n] for n in names]
        if any(len(side) != 1 for side in sides):
            continue
        first, second = sides[0][0], sides[1][0]
        first_line, second_line = _number(first.get("point")), _number(second.get("point"))
        first_price, second_price = _price(first.get("price")), _price(second.get("price"))
        if None in (first_line, second_line, first_price, second_price):
            continue
        if key == "spreads":
            if (
                first_line == _number(spread_home)
                and second_line == _number(spread_away)
                and first_line == -second_line
            ):
                prices["spread_home_price"], prices["spread_away_price"] = first_price, second_price
        elif first_line == second_line == _number(total):
            prices["total_over_price"], prices["total_under_price"] = first_price, second_price
    return prices
