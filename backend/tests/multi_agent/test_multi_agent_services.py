from app.services.agent_consensus_service import AgentConsensusService
from app.services.agent_conflict_service import AgentConflictService
from app.services.agent_coordinator_service import AgentCoordinatorService
from app.services.agent_debate_service import AgentDebateService
from app.services.agent_explanation_service import AgentExplanationService
from app.services.agent_message_service import AgentMessageService
from app.services.agent_weighting_service import AgentWeightingService


def test_agents_register_and_coordinator_assigns_tasks():
    coordinator = AgentCoordinatorService()
    assignment = coordinator.assign_task({"game": "Lakers vs Celtics"})

    assert "prediction_agent" in assignment
    assert "simulation_agent" in assignment


def test_messages_transmit_and_debate_executes():
    messages = AgentMessageService()
    sent = messages.send("simulation_agent", "risk_agent", "High variance due to injury uncertainty")
    debate = AgentDebateService().run(
        {
            "prediction_agent": "Celtics -4",
            "risk_agent": "PASS",
            "simulation_agent": "Celtics probability: 61%",
        }
    )

    assert sent["sender"] == "simulation_agent"
    assert "edge" in debate["debate"].lower()


def test_consensus_calculates_and_weighting_updates():
    consensus = AgentConsensusService().combine(
        {
            "prediction_confidence": 78,
            "simulation_confidence": 61,
            "research_confidence": 70,
            "risk_modifier": -4,
            "final_pick": "Celtics -4",
        }
    )
    weights = AgentWeightingService().update()

    assert consensus["final_pick"] == "Celtics -4"
    assert round(sum(weights["weights"].values()), 2) == 1.0


def test_conflicts_detected_and_explanations_generated():
    conflict = AgentConflictService().detect({"prediction_confidence": 82, "simulation_confidence": 48})
    explanation = AgentExplanationService().explain({"recommended": "PASS"})

    assert conflict["conflict"] == "HIGH"
    assert explanation["recommended"] == "PASS"


def test_coordinator_collect_results_shapes_outputs():
    coordinator = AgentCoordinatorService()
    output = coordinator.coordinate_analysis({"game": "Chiefs vs Bills"})

    assert output["results"]["consensus"]["confidence"] > 0
    assert output["results"]["reputation"]["weight"] in {"HIGH", "MEDIUM"}
