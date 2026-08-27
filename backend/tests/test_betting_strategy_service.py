from app.services.betting_strategy_service import BettingStrategyService
from app.services.market_conflict_detector import MarketConflictDetector
from app.services.parlay_compatibility_service import ParlayCompatibilityService
from app.services.risk_service import RiskService


def test_bet_quality_stays_within_0_100():
    service = BettingStrategyService()
    score = service.calculate_quality_score(
        {
            "confidence": 90,
            "market_edge": 80,
            "historical_edge": 70,
            "risk_score": 10,
        }
    )

    assert 0 <= score <= 100


def test_risk_scores_calculate_correctly():
    service = RiskService()
    result = service.calculate_risk(
        {
            "uncertainty": "HIGH",
            "market_agreement": "STRONG",
            "sample_size": "LOW",
            "injury_uncertainty": True,
        }
    )

    assert result["risk_score"] == 72
    assert result["risk_level"] == "HIGH"


def test_pass_decisions_occur():
    service = BettingStrategyService()
    result = service.recommend_action(55)

    assert result["recommendation"] == "PASS"
    assert result["label"] == "➖ PASS"


def test_missing_market_data_is_handled():
    service = BettingStrategyService()
    result = service.evaluate_bet(prediction=None, market_value=None, confidence=80)

    assert result["value_score"] == 0
    assert result["recommendation"] == "AVOID"


def test_recommendations_remain_deterministic():
    service = BettingStrategyService()
    first = service.evaluate_bet(prediction=6, market_value=4, confidence=88)
    second = service.evaluate_bet(prediction=6, market_value=4, confidence=88)

    assert first == second


def test_parlay_conflicts_detected():
    service = ParlayCompatibilityService()
    result = service.calculate_compatibility_score(
        {"game_id": 10, "selection": "Team A -8"},
        {"game_id": 10, "selection": "Team A +8"},
    )

    assert result["correlation_score"] <= 30
    assert result["recommendation"] == "AVOID"


def test_market_conflict_levels_are_detected():
    detector = MarketConflictDetector()
    result = detector.detect_conflict(model_line=8, market_line=2)

    assert result["conflict_level"] == "HIGH_CONFLICT"
