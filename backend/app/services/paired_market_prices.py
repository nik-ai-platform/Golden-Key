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
    prices, _ = paired_market_prices_with_diagnostics(
        bookmaker,
        home_team,
        away_team,
        spread_home=spread_home,
        spread_away=spread_away,
        total=total,
    )
    return prices


def paired_market_prices_with_diagnostics(
    bookmaker: dict[str, Any],
    home_team: str,
    away_team: str,
    *,
    spread_home: Any,
    spread_away: Any,
    total: Any,
) -> tuple[dict[str, int | None], dict[str, int]]:
    prices: dict[str, int | None] = {
        "spread_home_price": None,
        "spread_away_price": None,
        "total_over_price": None,
        "total_under_price": None,
    }
    diagnostics: dict[str, int] = {}
    markets_by_key: dict[str, list[dict[str, Any]]] = {
        "spreads": [],
        "totals": [],
    }
    for market in bookmaker.get("markets", []):
        key = market.get("key")
        if key in markets_by_key:
            markets_by_key[key].append(market)

    market_specs = (
        (
            "spreads",
            (home_team, away_team),
            (spread_home, spread_away),
            ("spread_home_price", "spread_away_price"),
        ),
        (
            "totals",
            ("Over", "Under"),
            (total, total),
            ("total_over_price", "total_under_price"),
        ),
    )
    for market_key, names, expected_lines, price_fields in market_specs:
        candidates = markets_by_key[market_key]
        prefix = "spread" if market_key == "spreads" else "total"
        if not candidates:
            diagnostics[f"{prefix}_market_missing"] = 1
            continue

        failure_reasons: set[str] = set()
        captured = False
        for market in candidates:
            sides = [
                [
                    outcome
                    for outcome in market.get("outcomes", [])
                    if outcome.get("name") == name
                ]
                for name in names
            ]
            if any(len(side) != 1 for side in sides):
                failure_reasons.add("outcome_pair_unavailable")
                continue

            first, second = sides[0][0], sides[1][0]
            first_line = _number(first.get("point"))
            second_line = _number(second.get("point"))
            wanted_first = _number(expected_lines[0])
            wanted_second = _number(expected_lines[1])
            if (
                first_line is None
                or second_line is None
                or wanted_first is None
                or wanted_second is None
                or first_line != wanted_first
                or second_line != wanted_second
                or (
                    market_key == "spreads"
                    and first_line != -second_line
                )
                or (
                    market_key == "totals"
                    and first_line != second_line
                )
            ):
                failure_reasons.add("line_mismatch")
                continue

            first_price = _price(first.get("price"))
            second_price = _price(second.get("price"))
            if first_price is None or second_price is None:
                failure_reasons.add("price_missing_or_invalid")
                continue

            prices[price_fields[0]] = first_price
            prices[price_fields[1]] = second_price
            diagnostics[f"{prefix}_pair_captured"] = 1
            captured = True
            break

        if captured:
            continue
        reason = next(
            (
                name
                for name in (
                    "price_missing_or_invalid",
                    "line_mismatch",
                    "outcome_pair_unavailable",
                )
                if name in failure_reasons
            ),
            "outcome_pair_unavailable",
        )
        diagnostics[f"{prefix}_{reason}"] = 1

    return prices, diagnostics
