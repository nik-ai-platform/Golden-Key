from app.services.clv_service import CLVService
from app.services.line_shopping_service import LineShoppingService
from app.services.market_data_service import MarketDataService
from app.services.market_intelligence_service import MarketIntelligenceService
from app.services.market_movement_service import MarketMovementService
from app.services.value_alert_service import ValueAlertService


def test_spread_edge_calculates_correctly():
    service = MarketIntelligenceService()

    assert service.calculate_spread_edge(7.2, 3.5) == 3.7


def test_moneyline_conversion_works():
    service = MarketIntelligenceService()

    assert service.calculate_moneyline_value(68.0, -150) == 8.0


def test_totals_comparison_works():
    service = MarketIntelligenceService()

    assert service.calculate_total_edge(226.8, 221.5) == 5.3


def test_missing_odds_handled_safely():
    service = MarketIntelligenceService()

    result = service.calculate_value(
        {
            "predicted_margin": 7.2,
            "win_probability": 68.0,
            "projected_total": 226.8,
            "confidence": 86.0,
        },
        {},
    )

    assert result["moneyline_edge"] == 0.0
    assert result["spread_edge"] == 0.0


def test_market_movement_stored_correctly():
    service = MarketIntelligenceService()

    result = service.calculate_value(
        {
            "predicted_margin": 7.2,
            "win_probability": 68.0,
            "projected_total": 226.8,
            "confidence": 86.0,
        },
        {
            "sportsbook_spread": 3.5,
            "odds": -150,
            "market_total": 221.5,
            "opening_line": -2.0,
            "current_line": -4.0,
        },
    )

    assert result["line_movement"] == -2.0


def test_value_scores_remain_bounded_0_100():
    service = MarketIntelligenceService()

    result = service.calculate_value(
        {
            "predicted_margin": 50.0,
            "win_probability": 99.0,
            "projected_total": 300.0,
            "confidence": 100.0,
            "historical_edge": 100.0,
        },
        {
            "sportsbook_spread": 1.0,
            "odds": 500,
            "market_total": 150.0,
            "opening_line": -10.0,
            "current_line": -1.0,
        },
    )

    assert 0.0 <= result["value_score"] <= 100.0


def test_odds_import_and_best_line_selection():
    market_service = MarketDataService()
    ingested = market_service.ingest_odds({"game_id": 1, "sportsbook": "DraftKings", "spread": "KC -3", "moneyline": "-110"})
    assert ingested["sportsbook"] == "DraftKings"

    line_service = LineShoppingService()
    best = line_service.find_best_line("Lakers vs Celtics", [
        {"book": "Book A", "line": "Lakers -4.5", "price": "-110"},
        {"book": "Book B", "line": "Lakers -4", "price": "-105"},
        {"book": "Book C", "line": "Lakers -5", "price": "-115"},
    ])
    assert best["book"] == "Book B"
    assert best["best_line"] == "Lakers -4"


def test_movement_clv_and_alerts_work():
    movement = MarketMovementService().detect_movement(2, 5)
    assert movement["signal"] == "Strong Money Movement"

    clv = CLVService().calculate_clv(3, 5)
    assert clv == 2.0

    alert = ValueAlertService().check(6, 4.5)
    assert alert is not None
    assert alert["alert"].startswith("🔥")
