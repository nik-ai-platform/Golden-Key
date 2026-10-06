"""Versioned production metric semantics; never mutates persisted predictions."""

import logging
import re
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from collections.abc import Mapping

from sqlalchemy import and_, case, func, or_
from sqlalchemy.sql.elements import ColumnElement

logger = logging.getLogger(__name__)

LEGACY_MODEL_VERSION = "NPI-4.0"
MODEL_VERSION = "NPI-5.0"
SUPPORTED_MODEL_VERSIONS = {LEGACY_MODEL_VERSION, "NPI-4.1", MODEL_VERSION}
ACTIONABLE_THRESHOLDS = {"spread": 5.0, "moneyline": 3.0, "total": 2.0}
MARKET_SELECTIONS = {
    "spread": {"HOME", "AWAY"},
    "moneyline": {"HOME", "AWAY"},
    "total": {"OVER", "UNDER"},
}
METADATA_WHITESPACE = " \t\r\n"
SELECTION_TOKENS = ("HOME", "AWAY", "OVER", "UNDER", "PASS")


def _metadata_token(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.translate(str.maketrans("", "", METADATA_WHITESPACE)).lower()


def parse_market(value: object) -> str | None:
    token = _metadata_token(value)
    return token if token in MARKET_SELECTIONS else None


def parse_selection(value: object) -> str | None:
    token = _metadata_token(value)
    return next((selection for selection in SELECTION_TOKENS if selection.lower() == token), None)


def supported_metadata(market: object, selection: object) -> bool:
    market, selection = parse_market(market), parse_selection(selection)
    return market is not None and (
        selection == "PASS" or selection in MARKET_SELECTIONS[market]
    )


def _sql_metadata_token(value: ColumnElement) -> ColumnElement:
    token = value
    for whitespace in METADATA_WHITESPACE:
        token = func.replace(token, whitespace, "")
    return func.lower(token)


def sql_market(value: ColumnElement) -> ColumnElement:
    token = _sql_metadata_token(value)
    return case((token.in_(tuple(MARKET_SELECTIONS)), token), else_=None)


def sql_selection(value: ColumnElement) -> ColumnElement:
    token = _sql_metadata_token(value)
    return case(
        *((token == selection.lower(), selection) for selection in SELECTION_TOKENS),
        else_=None,
    )


def sql_supported_metadata(market: ColumnElement, selection: ColumnElement) -> ColumnElement:
    market, selection = sql_market(market), sql_selection(selection)
    return or_(*(
        and_(market == name, selection.in_((*sorted(selections), "PASS")))
        for name, selections in MARKET_SELECTIONS.items()
    ))


def metric_version(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"NPI-(4|5)\.(0|1)", value)
    if match is None or value not in SUPPORTED_MODEL_VERSIONS:
        return None
    return int(match[1]), int(match[2])


def is_legacy_version(value: object) -> bool:
    version = metric_version(value)
    return version is not None and version[0] == 4


def finite_metric(value: object) -> float | None:
    if not isinstance(value, Real) or isinstance(value, bool):
        if value is not None:
            logger.warning("Invalid prediction numeric metric type is unavailable")
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        logger.warning("Unrepresentable prediction metric is unavailable")
        return None
    if not isfinite(number):
        logger.warning("Nonfinite prediction metric is unavailable")
        return None
    return number


def historical_integer(value: object) -> int | None:
    number = finite_metric(value)
    if number is None:
        return None
    if not number.is_integer():
        logger.warning("Invalid historical integer metric is unavailable")
        return None
    return int(number)


def historical_text(value: object, *, fallback: str | None = None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if value is not None:
        logger.warning("Invalid historical text metric is unavailable")
    return fallback


def historical_probability(value: object) -> float | None:
    probability = finite_metric(value)
    if probability is not None and not 0 <= probability <= 100:
        logger.warning("Out-of-range historical prediction probability is unavailable")
        return None
    return probability


def historical_price(value: object) -> int | None:
    price = finite_metric(value)
    if price is None:
        return None
    if not price.is_integer() or abs(price) < 100:
        logger.warning("Invalid historical American odds are unavailable")
        return None
    return int(price)


def actionable_prediction(prediction: object) -> bool:
    """Completeness only; market thresholds and price policy remain separate."""
    def value(name: str) -> object:
        if isinstance(prediction, Mapping):
            return prediction.get(name)
        return getattr(prediction, name, None)

    market = parse_market(value("market"))
    selection = parse_selection(value("selection"))
    version = value("model_version")
    probability = selected_side_probability(
        value("simulation_probability"), market=market,
        selection=selection, model_version=version,
    )
    edge = describe_edge(
        value("projected_edge"), market=market, selection=selection, model_version=version,
    )
    return (
        probability is not None
        and finite_metric(value("npi_score")) is not None
        and finite_metric(value("confidence_score")) is not None
        and edge.selected_side_value is not None
        and historical_price(value("american_odds")) is not None
        and (market == "moneyline" or finite_metric(value("line_value")) is not None)
    )


def normalized_text(value: object, *, upper: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().upper() if upper else value.strip().lower()


def bounded_probability(value: object) -> float | None:
    if value is None:
        return None
    probability = finite_metric(value)
    if probability is None:
        return None
    return max(0.0, min(probability, 100.0))


def _supported(market: str | None, selection: str | None, model_version: object) -> bool:
    if metric_version(model_version) is None:
        logger.warning("Unsupported prediction metric model version is unavailable")
        return False
    if selection == "PASS":
        return False
    if selection not in MARKET_SELECTIONS.get(market, set()):
        logger.warning("Unsupported prediction market/selection is unavailable")
        return False
    return True


def selected_side_probability(
    value: object, *, market: object, selection: object, model_version: object,
) -> float | None:
    market, selection = parse_market(market), parse_selection(selection)
    if not _supported(market, selection, model_version):
        return None
    probability = historical_probability(value)
    if probability is None:
        return None
    if is_legacy_version(model_version) and market == "spread" and selection == "AWAY":
        return 100.0 - probability
    return probability


@dataclass(frozen=True)
class EdgeDescriptor:
    selected_side_value: float | None
    unit: str
    benchmark: str


def describe_edge(
    value: object, *, market: object, selection: object, model_version: object,
) -> EdgeDescriptor:
    market, selection = parse_market(market), parse_selection(selection)
    unit, benchmark = {
        "spread": ("percentage_points", "50_percent_cover_probability"),
        "moneyline": ("percentage_points", "vig_free_implied_probability"),
        "total": ("scoring_points", "posted_total"),
    }.get(market, ("unavailable", "unavailable"))
    if not _supported(market, selection, model_version) or value is None:
        return EdgeDescriptor(None, unit, benchmark)
    selected_value = finite_metric(value)
    if selected_value is None:
        return EdgeDescriptor(None, unit, benchmark)
    if is_legacy_version(model_version) and (
        (market == "spread" and selection == "AWAY")
        or (market == "total" and selection == "UNDER")
    ):
        selected_value = -selected_value
    return EdgeDescriptor(selected_value, unit, benchmark)


def qualifies_edge(value: float | None, market: str) -> bool:
    value = finite_metric(value)
    market = parse_market(market)
    if value is None:
        return False
    if market == "spread":
        return value > 5
    if market == "moneyline":
        return value >= 3
    if market == "total":
        return value >= 2
    return False


def edge_ranking_strength(value: object, market: object) -> float | None:
    """Dimensionless threshold multiples for ranking, never a betting metric."""
    edge = finite_metric(value)
    threshold = ACTIONABLE_THRESHOLDS.get(parse_market(market))
    if edge is None or threshold is None:
        return None
    return max(0.0, edge) / threshold


def corrected_generation_version(configured_version: str) -> str:
    if metric_version(configured_version) is None:
        raise ValueError(f"Unsupported production metric model version: {configured_version}")
    return MODEL_VERSION


def metric_reasoning(reasoning: str | None, probability: float | None) -> str | None:
    if reasoning is None:
        return None
    display = "unavailable" if probability is None else f"{probability:g}%"
    return re.sub(
        r"(?:Simulation|Model) Probability:\s*(?:[+-]?\d+(?:\.\d+)?|None|nan|inf)%",
        f"Model Probability: {display}",
        reasoning,
        flags=re.IGNORECASE,
    )
