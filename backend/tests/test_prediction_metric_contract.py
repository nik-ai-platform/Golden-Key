from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.prediction import PredictionCreate
from app.services.prediction_engine import PredictionEngine
from app.services.prediction_metric_contract import (
    bounded_probability,
    corrected_generation_version,
    describe_edge,
    qualifies_edge,
    selected_side_probability,
)
from app.services.v1_read_service import V1ReadService


@pytest.mark.parametrize(
    ("market", "selection", "version", "raw", "expected"),
    [
        ("spread", "HOME", "NPI-4.0", 62, 62),
        ("spread", "AWAY", "NPI-4.0", 35, 65),
        ("spread", "AWAY", "NPI-4.1", 35, 65),
        ("spread", "AWAY", "NPI-5.0", 65, 65),
        ("spread", "HOME", "NPI-5.0", 62, 62),
        ("moneyline", "AWAY", "NPI-4.0", 38.53, 38.53),
        ("moneyline", "HOME", "NPI-5.0", 70, 70),
        ("total", "OVER", "NPI-4.0", 65, 65),
        ("total", "UNDER", "NPI-4.0", 65, 65),
        ("total", "UNDER", "NPI-5.0", 65, 65),
        ("spread", "PASS", "NPI-5.0", 50, None),
        ("spread", "AWAY", "unknown", 35, None),
        ("spread", "AWAY", None, 35, None),
        ("spread", "invalid", "NPI-5.0", 35, None),
        ("spread", "AWAY", "NPI-4.0", None, None),
        ("spread", "AWAY", "NPI-5.0", float("nan"), None),
        ("spread", "HOME", "NPI-5.0", float("inf"), None),
        ("spread", "HOME", "NPI-5.0", -10, None),
        ("spread", "HOME", "NPI-5.0", 110, None),
        ("spread", "AWAY", "NPI-4.0", 110, None),
    ],
)
def test_selected_side_probability(market, selection, version, raw, expected):
    assert selected_side_probability(
        raw, market=market, selection=selection, model_version=version,
    ) == expected


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf")])
def test_unavailable_probability_does_not_become_zero(value):
    assert bounded_probability(value) is None


@pytest.mark.parametrize(
    ("market", "selection", "version", "raw", "expected", "unit"),
    [
        ("spread", "HOME", "NPI-4.0", 12, 12, "percentage_points"),
        ("spread", "AWAY", "NPI-4.0", -15, 15, "percentage_points"),
        ("spread", "AWAY", "NPI-5.0", 15, 15, "percentage_points"),
        ("moneyline", "AWAY", "NPI-4.0", 3, 3, "percentage_points"),
        ("total", "OVER", "NPI-4.0", 2, 2, "scoring_points"),
        ("total", "UNDER", "NPI-4.0", -2, 2, "scoring_points"),
        ("total", "UNDER", "NPI-5.0", 2, 2, "scoring_points"),
        ("total", "UNDER", "unknown", -2, None, "scoring_points"),
        ("total", "PASS", "NPI-5.0", 1, None, "scoring_points"),
    ],
)
def test_edge_descriptor(market, selection, version, raw, expected, unit):
    edge = describe_edge(raw, market=market, selection=selection, model_version=version)
    assert edge.selected_side_value == expected
    assert edge.unit == unit


@pytest.mark.parametrize(
    ("market", "edge", "expected"),
    [("spread", 5, False), ("spread", 5.01, True),
     ("moneyline", 2.99, False), ("moneyline", 3, True),
     ("total", 1.99, False), ("total", 2, True), ("total", -2, False)],
)
def test_actionable_edge_thresholds(market, edge, expected):
    assert qualifies_edge(edge, market) is expected


@pytest.mark.parametrize(("edge", "selection"), [(-5.01, "AWAY"), (-5, "PASS"), (5, "PASS"), (5.01, "HOME")])
def test_spread_selection_boundaries(edge, selection):
    assert PredictionEngine().determine_pick(None, None, edge) == selection


@pytest.mark.parametrize(("probability", "selection"), [(65, "HOME"), (35, "AWAY"), (50, "PASS")])
def test_new_spread_probability_confidence_and_risk(probability, selection):
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.return_value = {
        "win_probability": probability, "runs": 10000, "average_margin": 0,
    }
    odds = SimpleNamespace(
        spread_home=-3.5, spread_away=3.5,
        moneyline_home=-220, moneyline_away=180, total=48.5,
    )
    result = engine._market_specifications("NFL", odds, {"npi_score": 100, "factors": []})[0]
    assert result["selection"] == selection
    assert result["simulation_probability"] == (65 if selection != "PASS" else None)
    if selection != "PASS":
        assert result["confidence_score"] == engine.calculate_confidence(100, 15, {"win_probability": 65})
        assert result["projected_edge"] == 15
        assert result["risk_level"] == engine.calculate_risk(result["confidence_score"], 15)


@pytest.mark.parametrize(
    ("home_line", "home_cover_probability", "selection", "selected_line", "probability", "edge"),
    [
        (-3.5, 60.0, "HOME", -3.5, 60.0, 10.0),
        (3.5, 60.0, "HOME", 3.5, 60.0, 10.0),
        (-3.5, 40.0, "AWAY", 3.5, 60.0, 10.0),
        (3.5, 40.0, "AWAY", -3.5, 60.0, 10.0),
        (38.5, 99.99, "HOME", 38.5, 99.99, 49.99),
        (-38.5, 0.01, "AWAY", 38.5, 99.99, 49.99),
        (-0.5, 50.0, "PASS", -0.5, None, 0.0),
    ],
)
def test_spread_selection_preserves_signed_provider_side_and_legacy_metrics(
    home_line,
    home_cover_probability,
    selection,
    selected_line,
    probability,
    edge,
):
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.return_value = {
        "win_probability": home_cover_probability,
        "runs": 10000,
        "average_margin": home_line,
    }
    odds = SimpleNamespace(
        spread_home=home_line,
        spread_away=-home_line,
        moneyline_home=-150,
        moneyline_away=130,
        total=48.5,
    )

    result = engine._market_specifications(
        "NFL",
        odds,
        {"npi_score": 100, "factors": []},
    )[0]

    assert result["selection"] == selection
    assert result["line_value"] == selected_line
    assert result["simulation_probability"] == probability
    assert result["projected_edge"] == edge
    engine.simulation_engine.simulate.assert_called_once_with(
        npi_score=100,
        spread=home_line,
    )


@pytest.mark.parametrize(("confidence", "risk"), [(64.99, "high"), (65, "medium"), (79.99, "medium"), (80, "low"), (95, "low")])
def test_risk_boundaries(confidence, risk):
    assert PredictionEngine().calculate_risk(confidence, 0) == risk


@pytest.mark.parametrize(
    ("posted", "selection", "probability", "edge"),
    [(40.5, "OVER", 59, 3), (48.5, "UNDER", 59, 3),
     (44.5, "PASS", None, 0)],
)
def test_total_selected_side_probability(posted, selection, probability, edge):
    result = PredictionEngine()._total_specification("NFL", SimpleNamespace(total=posted))
    assert result["selection"] == selection
    assert result["simulation_probability"] == probability
    assert result["projected_edge"] == edge


@pytest.mark.parametrize(("edge", "selection"), [(-2, "UNDER"), (2, "OVER"), (-1.999, "PASS"), (1.999, "PASS")])
def test_total_exact_threshold(edge, selection):
    # Unknown sports use the posted total; supply a baseline yielding the exact edge.
    engine = PredictionEngine()
    engine.SPORT_TOTAL_BASELINES = {"TEST": edge / 0.75}
    assert engine._total_specification("TEST", SimpleNamespace(total=0))["selection"] == selection


@pytest.mark.parametrize(("edge", "expected"), [(2.99, "PASS"), (3, "HOME")])
def test_moneyline_exact_threshold(edge, expected):
    engine = PredictionEngine()
    engine._spread_home_win_probability = MagicMock(return_value=50 + edge)
    odds = SimpleNamespace(moneyline_home=100, moneyline_away=100, spread_home=0)
    result = engine._moneyline_specification(odds, {"factors": []})
    assert result["selection"] == expected
    assert result["simulation_probability"] == (53 if expected == "HOME" else None)


@pytest.mark.parametrize(("version", "raw", "expected"), [
    ("NPI-4.0", 35, 65), ("NPI-4.1", 35, 65), ("NPI-5.0", 65, 65),
    ("NPI-5.0", None, None), ("NPI-5.0", float("nan"), None),
    ("unknown", 35, None),
])
def test_customer_serialization_preserves_historical_confidence_and_risk(version, raw, expected):
    prediction = SimpleNamespace(
        id=1, market="spread", selection="AWAY", line_value=3.5, american_odds=-110,
        sportsbook="Test", odds_observed_at=None, model_version=version,
        npi_score=100, confidence_score=70, simulation_probability=raw,
        projected_edge=15 if version == "NPI-5.0" else -15,
        risk_level="medium", reasoning=f"NPI Score: 100/200 Simulation Probability: {raw}%",
    )
    item = V1ReadService()._prediction_item(
        prediction, SimpleNamespace(id=1, sport="NFL", game_date=datetime(2026, 10, 6)),
        SimpleNamespace(name="Home"), SimpleNamespace(name="Away"),
    )
    assert item["simulation_probability"] == expected
    assert item["selected_side_edge"] == (None if version == "unknown" else 15)
    assert item["confidence_score"] == 70
    assert item["risk_level"] == "medium"
    assert prediction.simulation_probability is raw
    assert item["model_version"] == version
    display = "unavailable" if expected is None else "65%"
    assert item["reasoning"] == f"NPI Score: 100/200 Model Probability: {display}"
    assert prediction.reasoning.endswith(f"{raw}%")
    assert item["recommendation_eligible"] is (expected is not None)


@pytest.mark.parametrize(("market", "selection", "edge", "unit"), [
    ("spread", "AWAY", -15, "pp"), ("moneyline", "AWAY", 3, "pp"),
    ("total", "UNDER", -2, "points"),
])
def test_ranking_reason_units(market, selection, edge, unit):
    item = {
        "market": market, "selection": selection, "model_version": "NPI-4.0",
        "npi_score": 100, "confidence_score": 70, "projected_edge": edge,
        "simulation_probability": 65,
    }
    reasons = V1ReadService()._daily_card_pick(item, role="TEST", label="Test")["ranking_reasons"]
    edge_reason = next(reason for reason in reasons if "projected edge" in reason)
    assert f" {unit} " in edge_reason
    assert "%" not in edge_reason


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf")])
def test_creation_schema_rejects_invalid_probabilities(value):
    with pytest.raises(ValidationError):
        PredictionCreate(
            game_id=1, market="spread", selection="HOME", model_version="NPI-5.0",
            npi_score=100, simulation_probability=value,
        )


def test_generation_version_mapping_and_unknown_version():
    assert corrected_generation_version("NPI-4.0") == "NPI-5.0"
    assert corrected_generation_version("NPI-4.1") == "NPI-5.0"
    assert corrected_generation_version("NPI-5.0") == "NPI-5.0"
    with pytest.raises(ValueError, match="Unsupported production metric"):
        corrected_generation_version("NPI-unknown")


def test_pass_is_not_a_daily_card_actionable_pick():
    item = {
        "prediction_id": 1, "market": "spread", "selection": "PASS",
        "model_version": "NPI-5.0", "npi_score": 100, "american_odds": -110,
    }
    card = V1ReadService()._build_daily_card([item])
    assert card["best_bet"] is None
    assert card["featured_picks"] == []


@pytest.mark.parametrize(("version", "raw"), [("NPI-4.0", 35), ("NPI-4.1", 35), ("NPI-5.0", 65)])
def test_performance_uses_the_same_probability_contract(version, raw):
    prediction = SimpleNamespace(
        market="spread", selection="AWAY", model_version=version, simulation_probability=raw,
    )
    calibration, brier = V1ReadService._spread_probability_calibration([
        (prediction, SimpleNamespace(outcome="WIN"), object()),
    ])
    row = next(row for row in calibration if row["sample_size"])
    assert row["predicted_probability_average"] == selected_side_probability(
        raw, market="spread", selection="AWAY", model_version=version,
    )
    assert brier == pytest.approx([0.35 ** 2])


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -float("inf")])
def test_unavailable_edge_preserves_units_without_manufacturing_zero(value):
    descriptor = describe_edge(
        value, market="total", selection="UNDER", model_version="NPI-5.0",
    )
    assert descriptor.selected_side_value is None
    assert descriptor.unit == "scoring_points"
    assert descriptor.benchmark == "posted_total"


def test_protected_history_returns_only_latest_market_rows_without_mutation():
    old = SimpleNamespace(id=1, game_id=1, market="spread", selection="HOME", model_version="NPI-4.0")
    new = SimpleNamespace(id=2, game_id=1, market="spread", selection="HOME", model_version="NPI-5.0")
    assert PredictionEngine()._ordered_predictions([old, new]) == [new]
    assert old.model_version == "NPI-4.0"


@pytest.mark.parametrize("field", ["market", "selection", "model_version"])
@pytest.mark.parametrize("value", [None, "", " ", 17, [], {}, float("nan"), float("inf")])
def test_invalid_metadata_is_unavailable_without_raising(field, value, caplog):
    metadata = {"market": "spread", "selection": "AWAY", "model_version": "NPI-4.0"}
    metadata[field] = value
    assert selected_side_probability(35, **metadata) is None
    assert describe_edge(-15, **metadata).selected_side_value is None
    assert caplog.records


@pytest.mark.parametrize("version", ["NPI-v1", "NBA-NPI-v4", "NPI-4.10", "NPI-4.0junk", "NPI-5.1"])
def test_unverified_families_are_unavailable(version):
    assert selected_side_probability(35, market="spread", selection="AWAY", model_version=version) is None


@pytest.mark.parametrize("value", ["35", "", [], {}, True, float("nan"), float("inf")])
def test_invalid_numeric_probability_is_unavailable(value, caplog):
    assert selected_side_probability(
        value, market="spread", selection="AWAY", model_version="NPI-4.0",
    ) is None
    assert describe_edge(
        value, market="spread", selection="AWAY", model_version="NPI-4.0",
    ).selected_side_value is None
    assert caplog.records


@pytest.mark.parametrize(("value", "expected"), [(-10, 0), (110, 100), (65, 65)])
def test_generated_probability_is_bounded_separately_from_historical_values(value, expected):
    assert bounded_probability(value) == expected


@pytest.mark.parametrize(("market", "edge", "strength"), [
    ("spread", 5, 1), ("moneyline", 3, 1), ("total", 2, 1),
    ("spread", 7.5, 1.5), ("moneyline", 4.5, 1.5), ("total", 3, 1.5),
])
def test_dimensionless_ranking_threshold_multiples(market, edge, strength):
    from app.services.prediction_metric_contract import edge_ranking_strength
    assert edge_ranking_strength(edge, market) == strength
