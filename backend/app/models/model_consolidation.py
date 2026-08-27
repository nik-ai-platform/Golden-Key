CANONICAL_MODELS = [
    "User",
    "Team",
    "Game",
    "Odds",
    "Prediction",
    "Simulation",
    "Portfolio",
    "Research",
    "Agent",
    "LearningEvent",
    "Organization",
]

# This list is intentionally metadata-only for safe incremental cleanup.
DEPRECATED_OR_MERGE_CANDIDATES = [
    "prediction_result",
    "prediction_evaluation",
    "prediction_history",
    "research_agent_job",
]

DEPRECATION_POLICY = {
    "prediction_results": {
        "replacement_table": "predictions_unified",
        "status": "deprecated",
        "notes": "Use unified prediction output records.",
    },
    "prediction_evaluations": {
        "replacement_table": "prediction_outcomes",
        "status": "deprecated",
        "notes": "Use outcome tracking and analytics snapshots.",
    },
    "prediction_history": {
        "replacement_table": "predictions_unified",
        "status": "deprecated",
        "notes": "History can be reconstructed from snapshots/outcomes.",
    },
    "research_agent_jobs": {
        "replacement_table": "research_tasks",
        "status": "deprecated",
        "notes": "Use autonomous research task schema.",
    },
}
