from app.services.ai_research_agent_service import AIResearchAgentService
from app.services.ai_research_report_service import AIResearchReportService
from app.services.ai_strategy_generator_service import AIStrategyGeneratorService
from app.services.experiment_evaluator_service import ExperimentEvaluatorService
from app.services.feature_discovery_service import FeatureDiscoveryService
from app.services.hypothesis_generator_service import HypothesisGeneratorService
from app.services.overfit_detection_service import OverfitDetectionService
from app.services.pattern_mining_service import PatternMiningService
from app.services.research_approval_service import ResearchApprovalService
from app.services.research_queue_service import ResearchQueueService


def test_research_jobs_start_and_analyze_objective():
    service = AIResearchAgentService()

    analysis = service.analyze_objective("Find NBA ATS edges involving rest advantage")

    assert analysis["sport"] == "NBA"
    assert analysis["focus"] == "rest advantage"
    assert analysis["priority"] == "high"


def test_feature_discovery_finds_meaningful_variables():
    service = FeatureDiscoveryService()

    discovery = service.discover_features({"sport": "NBA"})

    assert "travel" in discovery["features"]
    assert "back-to-back" in discovery["relationship"]


def test_pattern_detection_returns_repeatable_structures():
    service = PatternMiningService()

    patterns = service.mine_patterns({"sport": "NBA"})

    assert len(patterns) >= 4
    assert any("57.8" in str(item["historical_ats"]) for item in patterns)


def test_hypothesis_generation_converts_observations_into_tests():
    service = HypothesisGeneratorService()

    hypotheses = service.generate_hypotheses({"observation": "Road teams struggle after long travel", "sport": "NBA"})

    assert hypotheses[0]["hypothesis"].startswith("Fade road favorites")


def test_experiment_execution_and_strategy_building_work_together():
    agent_service = AIResearchAgentService()
    strategy_service = AIStrategyGeneratorService()

    hypothesis = agent_service.generate_hypotheses({"sport": "NBA", "focus": "rest advantage"})[0]
    strategy = strategy_service.build_strategy(hypothesis)
    results = agent_service.run_research(hypothesis)

    assert strategy["then"] == "Evaluate ATS performance"
    assert results["status"] == "completed"
    assert results["sample_size"] > 0


def test_overfit_detection_rejects_small_samples():
    service = OverfitDetectionService()

    reject = service.assess(20, 72.0)
    accept = service.assess(1500, 56.0)

    assert reject["status"] == "reject"
    assert accept["status"] == "accept"


def test_approval_workflow_advances_cleanly():
    service = ResearchApprovalService()

    review = service.review({"stage": "DISCOVERED", "approved": True})

    assert review["stage"] == "TESTING"
    assert review["approved"] is True


def test_reports_and_queue_outputs_are_generated():
    queue_service = ResearchQueueService()
    evaluator_service = ExperimentEvaluatorService()
    report_service = AIResearchReportService()

    job = queue_service.submit_request({"objective": "NBA ATS edges", "sport": "NBA"})
    evaluation = evaluator_service.evaluate({"sample_size": 48, "ats_percentage": 59.0, "roi": 11.4, "confidence": "medium"})
    report = report_service.generate_report(
        discovery={"relationship": "travel edge"},
        evidence={"patterns": []},
        backtest={"job": job},
        risk={"status": "review"},
        recommendation="Continue monitoring",
        next_steps=["Expand sample size"],
    )

    assert job["status"] == "queued"
    assert evaluation["overfitting_risk"] == "high"
    assert report["recommendation"] == "Continue monitoring"
