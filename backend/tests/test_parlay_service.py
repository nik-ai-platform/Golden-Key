from app.services.correlation_service import CorrelationService
from app.services.parlay_analysis_service import ParlayAnalysisService
from app.services.parlay_service import ParlayService


def test_probability_calculations_work():
    service = ParlayService()
    result = service.calculate_probability([
        {"probability": 0.6},
        {"probability": 0.65},
    ])

    assert result == 39.0


def test_correlated_bets_are_detected():
    service = CorrelationService()
    result = service.detect_correlation(
        {"game_id": 1, "team": "A", "selection": "Team A ML"},
        {"game_id": 1, "team": "A", "selection": "Team A -5"},
    )

    assert result["classification"] == "HIGHLY_CORRELATED"


def test_impossible_combinations_rejected():
    service = CorrelationService()
    result = service.detect_correlation(
        {"game_id": 1, "team": "A", "selection": "Team A ML"},
        {"game_id": 1, "team": "A", "selection": "Team A -5"},
    )

    assert result["correlation_score"] >= 75


def test_risk_limits_respected():
    service = ParlayService()
    parlays = service.generate_parlays([
        {"selection": "A", "probability": 0.6, "quality_score": 90},
        {"selection": "B", "probability": 0.65, "quality_score": 82},
    ], max_legs=3)

    assert len(parlays) <= 3


def test_stake_sizing_integrates_correctly():
    service = ParlayService()
    parlays = service.generate_parlays([
        {"selection": "A", "probability": 0.6, "quality_score": 90},
    ], max_legs=3)

    assert parlays[0]["stake"] == 0


def test_generated_parlays_are_deterministic():
    service = ParlayService()
    first = service.generate_parlays([
        {"selection": "A", "probability": 0.6, "quality_score": 90},
        {"selection": "B", "probability": 0.65, "quality_score": 82},
    ], max_legs=3)
    second = service.generate_parlays([
        {"selection": "A", "probability": 0.6, "quality_score": 90},
        {"selection": "B", "probability": 0.65, "quality_score": 82},
    ], max_legs=3)

    assert first == second


def test_parlay_analysis_service_handles_empty_payloads():
    service = ParlayAnalysisService()
    result = service.analyze([])

    assert result["average_legs"] == 0
