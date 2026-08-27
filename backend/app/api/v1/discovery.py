from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.services.autonomous_experiment_service import AutonomousExperimentService
from app.services.autonomous_hypothesis_service import AutonomousHypothesisService
from app.services.autonomous_improvement_service import AutonomousImprovementService
from app.services.discovery_memory_service import DiscoveryMemoryService
from app.services.knowledge_gap_service import KnowledgeGapService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.research_planner_service import ResearchPlannerService
from app.services.research_priority_service import ResearchPriorityService
from app.services.research_review_service import ResearchReviewService

router = APIRouter(prefix="/discovery", tags=["Autonomous Research"], dependencies=[Depends(require_analyst)])

planner_service = ResearchPlannerService()
gap_service = KnowledgeGapService()
hypothesis_service = AutonomousHypothesisService()
priority_service = ResearchPriorityService()
experiment_service = AutonomousExperimentService()
graph_service = KnowledgeGraphService()
memory_service = DiscoveryMemoryService()
review_service = ResearchReviewService()
improvement_service = AutonomousImprovementService()


@router.get("/tasks")
def get_tasks():
    opportunities = planner_service.identify_questions(
        {
            "sport": "NBA",
            "accuracy_decline_pct": 4,
            "market_shift_detected": True,
        }
    )
    prioritized = planner_service.prioritize_tasks(opportunities)
    scheduled = planner_service.schedule_research(prioritized)
    return {"tasks": scheduled}


@router.get("/findings")
def get_findings():
    gaps = gap_service.detect_gaps(
        {
            "sport": "NBA",
            "accuracy_decline_pct": 4,
            "unexplained_outcomes": 7,
            "market_shift_detected": True,
            "blind_spots": ["venue acoustics", "late travel swap"],
        }
    )
    hypothesis = hypothesis_service.generate({"observation": "Road favorites declining"})
    memory_entry = memory_service.store(
        {
            "question": "Weather impact NBA",
            "experiment": "Stratified weather index backtest",
            "result": "No meaningful edge",
            "lesson": "Do not prioritize",
        }
    )
    return {
        "gaps": gaps,
        "hypothesis": hypothesis,
        "memory_entry": memory_entry,
    }


@router.get("/experiments")
def get_experiments():
    task = {
        "objective": "Testing: Travel Fatigue Model",
        "sport": "NBA",
        "games": 15000,
        "baseline_roi": 0.0,
        "expected_uplift": 1.8,
    }
    report = experiment_service.run(task)
    return {"experiments": [report]}


@router.get("/proposals")
def get_proposals():
    candidate_tasks = [
        {
            "objective": "Fix NBA Rest Model",
            "potential_impact": 0.92,
            "confidence": 0.73,
            "data_availability": 0.88,
            "model_importance": 0.95,
            "expected_improvement": 0.79,
        },
        {
            "objective": "Analyze Weather Impact",
            "potential_impact": 0.41,
            "confidence": 0.38,
            "data_availability": 0.67,
            "model_importance": 0.33,
            "expected_improvement": 0.28,
        },
    ]
    ranked = priority_service.rank(candidate_tasks)
    top = ranked[0]
    proposal = improvement_service.propose(
        "NPI NBA",
        {
            "problem": "Rest weighting low",
            "suggested_change": "Increase weight +3",
            "expected_impact_pct": 1.2,
            "risk": "medium",
        },
    )
    queued = review_service.enqueue({
        "task": top,
        "proposal": proposal,
        "knowledge_graph": graph_service.build_graph({"sport": "NBA"}),
    })
    return {
        "ranked_tasks": ranked,
        "proposal": proposal,
        "review_queue": review_service.list_queue(),
        "queued": queued,
    }


@router.post("/approve")
def approve_proposal(payload: dict):
    return review_service.review(payload)
