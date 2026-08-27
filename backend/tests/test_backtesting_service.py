from datetime import date

from app.services.backtesting_service import BacktestingService


def _game(game_id, version_payload, actual_winner="home", confidence=72.0):
    predictions = {
        "NPI-v3": {"winner": "home", "confidence": confidence},
        "NPI-v4": {"winner": "away", "confidence": 61.0},
    }
    predictions.update(version_payload)

    return {
        "id": game_id,
        "sport": "nba",
        "game_date": date(2026, 1, 15).isoformat(),
        "home_team_id": "home",
        "away_team_id": "away",
        "home_score": 101,
        "away_score": 98,
        "actual_winner": actual_winner,
        "previous_games": [1, 2, 3],
        "previous_injuries": ["starter questionable"],
        "previous_odds": {"moneyline": -120},
        "previous_team_metrics": {"net_rating": 8.1},
        "future_rankings": {"home": 1},
        "future_performance": {"home": "hot"},
        "predictions": predictions,
    }


def test_historical_replay_produces_consistent_results():
    service = BacktestingService()
    games = [_game(1, {})]

    first = service.run_backtest("NPI-v3", date(2026, 1, 1), date(2026, 1, 31), sport="nba", games=games)
    second = service.run_backtest("NPI-v3", date(2026, 1, 1), date(2026, 1, 31), sport="nba", games=games)

    assert first["results"] == second["results"]
    assert first["report"] == second["report"]


def test_future_information_is_excluded():
    service = BacktestingService()
    output = service.simulate_predictions([_game(1, {})], "NPI-v3", model_version="NPI-v3")

    historical_inputs = output[0]["historical_inputs"]
    assert "future_rankings" not in historical_inputs
    assert "future_performance" not in historical_inputs
    assert output[0]["future_data_excluded"] is True


def test_metrics_calculate_correctly():
    service = BacktestingService()
    predictions = [
        {"predicted_winner": "home", "actual_winner": "home", "confidence": 80.0, "bet_outcome": "win"},
        {"predicted_winner": "away", "actual_winner": "home", "confidence": 60.0, "bet_outcome": "loss"},
    ]

    results = service.calculate_results(predictions)

    assert results["games_tested"] == 2
    assert results["accuracy"] == 50.0
    assert results["ats_record"] == "1-1"
    assert results["roi"] == 0.0


def test_model_versions_remain_isolated():
    service = BacktestingService()
    game = _game(1, {"NPI-v4": {"winner": "away", "confidence": 88.0}})

    v3 = service.simulate_predictions([game], "NPI-v3", model_version="NPI-v3")
    v4 = service.simulate_predictions([game], "NPI-v4", model_version="NPI-v4")

    assert v3[0]["predicted_winner"] == "home"
    assert v4[0]["predicted_winner"] == "away"


def test_failed_simulations_are_handled_safely():
    service = BacktestingService()

    def _broken_model(_payload):
        raise RuntimeError("boom")

    predictions = service.simulate_predictions([_game(1, {})], _broken_model)
    results = service.calculate_results(predictions)

    assert predictions[0]["status"] == "failed"
    assert results["failed_simulations"] == 1
    assert results["games_tested"] == 0


def test_large_datasets_process_correctly():
    service = BacktestingService()
    games = [_game(index, {}) for index in range(1, 1001)]

    outcome = service.run_backtest("NPI-v3", date(2026, 1, 1), date(2026, 1, 31), sport="nba", games=games)

    assert outcome["results"]["games_tested"] == 1000
    assert outcome["report"]["recommendation"] == "promote"
