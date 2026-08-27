from app.services.live_data_service import LiveDataService
from app.services.live_npi_service import LiveNPIService
from app.services.live_probability_service import LiveProbabilityService
from app.services.live_signal_service import LiveSignalService
from app.services.momentum_service import MomentumService


def test_live_state_and_events_update_correctly():
    service = LiveDataService()
    state = service.update_game_state({"game_id": 42, "sport": "NBA", "quarter_period": "Q3", "home_score": 82, "away_score": 76, "possession": "HOME", "momentum_score": 7})
    assert state["game_id"] == 42
    assert state["quarter_period"] == "Q3"


def test_live_npi_and_momentum_adjust_safely():
    npi = LiveNPIService().calculate_live_npi(158, 3, 5, -1, 2)
    assert npi == 167.0

    momentum = MomentumService().calculate_momentum(14, 60, 5, 2, 4, 1)
    assert momentum == 25.0


def test_probability_and_signals_are_logged():
    probabilities = LiveProbabilityService().estimate_probabilities(0.68, 0.62, 0.58)
    assert probabilities["win_probability"] == 68.0

    signal = LiveSignalService().generate_signal("VALUE", {"team": "Denver", "market": "+5", "model": "72% cover"})
    assert signal["signal"] == "VALUE"
