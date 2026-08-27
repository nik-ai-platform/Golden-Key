from app.services.ai_assistant_service import AIAssistantService
from app.services.game_monte_carlo_service import GameMonteCarloService
from app.services.game_scenario_service import GameScenarioService
from app.services.player_impact_simulation_service import PlayerImpactSimulationService
from app.services.possession_simulation_service import PossessionSimulationService
from app.services.simulation_engine_service import SimulationEngineService
from app.services.simulation_explanation_service import SimulationExplanationService
from app.services.simulation_value_service import SimulationValueService
from app.services.team_digital_twin_service import TeamDigitalTwinService


def test_simulations_execute_and_are_reproducible():
    service = SimulationEngineService()
    game = {"home_team": "Chiefs", "away_team": "Bills", "home_score": 27.4, "away_score": 23.1}

    first = service.run_simulation(game, 10000)
    second = service.run_simulation(game, 10000)

    assert first["probabilities"] == second["probabilities"]
    assert first["summary"]["favorite"] == "Chiefs"


def test_probability_calculation_and_value_detection_work():
    engine = SimulationEngineService()
    value_service = SimulationValueService()

    probabilities = engine.calculate_probabilities([
        {"winner": "Chiefs", "probability": 0.634},
        {"winner": "Bills", "probability": 0.366},
    ])
    value = value_service.find_value(62.0, 52.0)

    assert probabilities["Chiefs"] == 63.4
    assert value["edge"] == 10.0
    assert value["recommendation"] == "VALUE FOUND"


def test_scenario_changes_apply_to_simulation_outputs():
    service = GameScenarioService()

    result = service.simulate({"question": "What happens if rain increases?"})

    assert result["passing_efficiency"] == -8
    assert result["under_probability"] == 12


def test_player_and_possession_models_return_expected_impacts():
    player_service = PlayerImpactSimulationService()
    possession_service = PossessionSimulationService()

    player_out = player_service.simulate_impact("Starter Out")
    possession_out = possession_service.simulate_drive({"game": "Chiefs vs Bills"})

    assert player_out["win_probability_change"] == -11.5
    assert possession_out["touchdown"] == 28


def test_monte_carlo_and_explanations_match_results():
    monte_carlo_service = GameMonteCarloService()
    explanation_service = SimulationExplanationService()

    monte_carlo = monte_carlo_service.run({"home_team": "Chiefs", "away_team": "Bills"}, 50000)
    explanation = explanation_service.explain({"win_probability": 68})

    assert monte_carlo["score_distribution"]["Chiefs 24-30"] == 38
    assert "Defensive matchup" in explanation["explanation"]


def test_team_digital_twin_and_assistant_integration_are_safe():
    twin_service = TeamDigitalTwinService()
    assistant = AIAssistantService()

    twin = twin_service.build_twin({"name": "Kansas City Chiefs"})
    response = assistant.generate_response({"route": "Live Intelligence", "message": "What happens if their starting QB is out?"})

    assert twin["offense"] == 92
    assert "simulation" in response.lower()


def test_engine_summary_contains_score_context():
    service = SimulationEngineService()
    result = service.run_simulation({"home_team": "Chiefs", "away_team": "Bills"}, 10000)

    assert result["summary"]["average_score"]["home"] == 27.4
    assert result["summary"]["average_score"]["away"] == 23.1
