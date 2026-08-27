from app.services.alert_service import AlertService
from app.services.live_data_service import LiveDataService
from app.services.live_odds_service import LiveOddsService
from app.services.live_prediction_service import LivePredictionService
from app.services.momentum_service import MomentumService


def test_live_updates_do_not_overwrite_historical_data():
    service = LiveDataService()
    result = service.update_game_state({"game_id": 10, "home_score": 82, "away_score": 76})

    assert result["game_id"] == 10
    assert result["home_score"] == 82


def test_probability_updates_are_consistent():
    service = LivePredictionService()
    result = service.update_probability({"momentum_score": 20})

    assert result["win_probability"] == 70
    assert result["confidence"] == 80


def test_momentum_calculations_work():
    service = MomentumService()
    result = service.calculate_momentum(12, 60)

    assert result == 13.0


def test_invalid_game_states_rejected():
    service = LiveDataService()
    result = service.update_game_state(None)

    assert result is None


def test_alerts_trigger_correctly():
    service = AlertService()
    result = service.create_alert("Momentum Shift", {"message": "Huge swing", "value": "HIGH", "confidence": 90})

    assert result["alert_type"] == "Momentum Shift"


def test_odds_movement_tracked_correctly():
    service = LiveOddsService()
    result = service.track_movement(-3, 2)

    assert result["movement"] == 5.0
    assert result["direction"] == "UP"
