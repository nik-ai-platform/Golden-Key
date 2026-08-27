from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
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

router = APIRouter(prefix="/research-agent", tags=["Research Agent"], dependencies=[Depends(require_analyst)])

queue_service = ResearchQueueService()


@router.post("/start")
def start_research(payload: dict):
    objective = (payload.get("objective") or "Find new edges").strip()
    sport = (payload.get("sport") or "NBA").strip()

    agent_service = AIResearchAgentService()
    discovery_service = FeatureDiscoveryService()
    pattern_service = PatternMiningService()
    hypothesis_service = HypothesisGeneratorService()
    strategy_service = AIStrategyGeneratorService()
    evaluator_service = ExperimentEvaluatorService()
    overfit_service = OverfitDetectionService()
    report_service = AIResearchReportService()
    approval_service = ResearchApprovalService()

    analysis = agent_service.analyze_objective(objective)
    analysis["sport"] = sport or analysis.get("sport", "NBA")
    queue_job = queue_service.submit_request({"objective": objective, "sport": sport, "priority": analysis.get("priority", "normal")})
    hypotheses = agent_service.generate_hypotheses(analysis)
    feature_map = discovery_service.discover_features({"objective": objective, "sport": sport})
    patterns = pattern_service.mine_patterns({"objective": objective, "sport": sport})
    generated = hypothesis_service.generate_hypotheses({"observation": feature_map["relationship"], "sport": sport})
    strategy = strategy_service.build_strategy(generated[0])
    research_result = agent_service.run_research(generated[0])
    evaluation = evaluator_service.evaluate(research_result)
    risk = overfit_service.assess(research_result["sample_size"], research_result["ats_percentage"])
    report = report_service.generate_report(
        discovery=feature_map,
        evidence={"patterns": patterns, "hypotheses": hypotheses},
        backtest={"strategy": strategy, "results": research_result},
        risk=risk,
        recommendation=agent_service.summarize_results(research_result)["recommendation"],
        next_steps=["Run larger sample", "Approve strongest pattern", "Share with analyst review"],
    )
    approval = approval_service.review({"stage": "DISCOVERED", "approved": evaluation["overfitting_risk"] == "low"})

    return {
        "job": queue_job,
        "analysis": analysis,
        "discoveries": feature_map,
        "patterns": patterns,
        "hypotheses": hypotheses,
        "strategy": strategy,
        "results": research_result,
        "evaluation": evaluation,
        "risk": risk,
        "report": report,
        "approval": approval,
    }


@router.get("/jobs")
def list_jobs():
    return {"jobs": queue_service.list_jobs()}


@router.get("/discoveries")
def list_discoveries():
    service = FeatureDiscoveryService()
    patterns = PatternMiningService().mine_patterns({"sport": "NBA"})
    return {
        "discoveries": service.discover_features({"sport": "NBA"}),
        "patterns": patterns,
    }


@router.post("/approve")
def approve_research(payload: dict):
    service = ResearchApprovalService()
    return service.review(payload)
