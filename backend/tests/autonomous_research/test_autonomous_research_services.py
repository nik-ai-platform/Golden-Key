from app.services.autonomous_experiment_service import AutonomousExperimentService
from app.services.autonomous_hypothesis_service import AutonomousHypothesisService
from app.services.autonomous_improvement_service import AutonomousImprovementService
from app.services.discovery_memory_service import DiscoveryMemoryService
from app.services.knowledge_gap_service import KnowledgeGapService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.research_planner_service import ResearchPlannerService
from app.services.research_priority_service import ResearchPriorityService
from app.services.research_review_service import ResearchReviewService


def test_tasks_generated_from_declining_accuracy():
    planner = ResearchPlannerService()

    opportunities = planner.identify_questions({"sport": "NBA", "accuracy_decline_pct": 4})
    prioritized = planner.prioritize_tasks(opportunities)
    scheduled = planner.schedule_research(prioritized)

    assert opportunities
    assert prioritized[0]["priority"] == "high"
    assert scheduled[0]["status"] == "scheduled"


def test_knowledge_gaps_detected():
    service = KnowledgeGapService()
    result = service.detect_gaps({"sport": "NBA", "accuracy_decline_pct": 3.8, "unexplained_outcomes": 8})

    categories = {item["category"] for item in result["findings"]}
    assert "Performance Declines" in categories
    assert "Unexplained Outcomes" in categories
    assert "Model Weaknesses" in categories


def test_hypotheses_created_from_observations():
    service = AutonomousHypothesisService()
    result = service.generate({"observation": "Road favorites declining"})

    assert "Travel fatigue" in result["testable_hypothesis"]
    assert "dataset" in result["experiment_design"]


def test_experiments_execute_with_pipeline_outputs():
    service = AutonomousExperimentService()
    report = service.run({"objective": "Travel Fatigue Model", "sport": "NBA", "games": 15000, "expected_uplift": 1.8})

    assert report["dataset_selection"]["games_selected"] == 15000
    assert report["report"]["impact"] == "+1.8% ROI"


def test_knowledge_stored_and_repeat_failures_deprioritized():
    service = DiscoveryMemoryService()
    service.store(
        {
            "question": "Weather impact NBA",
            "experiment": "Weather-stratified ATS backtest",
            "result": "No meaningful edge",
            "lesson": "Do not prioritize",
        }
    )

    assert service.should_deprioritize("Weather impact NBA") is True


def test_improvements_proposed_with_validation_requirements():
    service = AutonomousImprovementService()
    proposal = service.propose(
        "NPI NBA",
        {
            "problem": "Rest weighting low",
            "suggested_change": "Increase weight +3",
            "expected_impact_pct": 1.2,
            "risk": "medium",
        },
    )

    assert proposal["current_model"] == "NPI NBA"
    assert proposal["expected_impact"] == "+1.2% ATS"
    assert len(proposal["required_validation"]) == 3


def test_approval_workflow_and_priority_and_graph_outputs():
    review = ResearchReviewService()
    queued = review.enqueue({"title": "Fix NBA Rest Model"})
    approved = review.review({"id": queued["id"], "decision": "approve"})

    ranking = ResearchPriorityService().rank(
        [
            {
                "objective": "Fix NBA Rest Model",
                "potential_impact": 0.92,
                "confidence": 0.72,
                "data_availability": 0.88,
                "model_importance": 0.95,
                "expected_improvement": 0.79,
            },
            {
                "objective": "Analyze Weather Impact",
                "potential_impact": 0.4,
                "confidence": 0.35,
                "data_availability": 0.7,
                "model_importance": 0.3,
                "expected_improvement": 0.25,
            },
        ]
    )
    graph = KnowledgeGraphService().build_graph({"sport": "NBA"})

    assert approved["status"] == "approved"
    assert ranking[0]["objective"] == "Fix NBA Rest Model"
    assert graph["path_example"][0] == "Back-to-back"
