from app.services.adaptive_npi_optimizer_service import AdaptiveNPIOptimizerService
from app.services.feature_evolution_service import FeatureEvolutionService
from app.services.learning_engine_service import LearningEngineService
from app.services.market_regime_service import MarketRegimeService
from app.services.model_improvement_service import ModelImprovementService
from app.services.model_monitoring_service import ModelMonitoringService
from app.services.prediction_feedback_service import PredictionFeedbackService


def test_events_captured_and_feedback_processed():
    feedback = PredictionFeedbackService().process({"prediction": "Team A -5"}, {"result": "Team A loses"})

    assert feedback["error_score"] == 1.0
    assert feedback["learning_signal"] == "Store learning signal"


def test_performance_tracking_and_error_analysis():
    engine = LearningEngineService()

    outcomes = [
        {"prediction": "Celtics cover", "actual_result": "Failed", "error_score": 1.0},
        {"prediction": "Lakers win", "actual_result": "Lakers win", "error_score": 0.0},
    ]
    analysis = engine.analyze_results(outcomes)
    errors = engine.identify_errors(outcomes)

    assert analysis["total_outcomes"] == 2
    assert errors[0]["error_score"] == 1.0


def test_feature_analysis_and_npi_proposals_work():
    evolution = FeatureEvolutionService().evolve({"rest": 8})
    optimizer = AdaptiveNPIOptimizerService().optimize({"proposal": "Increase travel penalty: +2 points"})

    assert evolution["suggested_update"]["rest"] == 11.0
    assert optimizer["historical_improvement"] == "+1.4% ROI"


def test_approval_workflow_and_version_recommendations_work():
    improvement = ModelImprovementService().recommend("Road teams undervalued")
    monitoring = ModelMonitoringService().monitor({"prediction_accuracy": 51.0})
    regime = MarketRegimeService().detect({"scoring": 212, "public_bias": True})

    assert improvement["risk_level"] == "Low"
    assert monitoring["alert"]
    assert regime["regime"] == "Public Betting Bias"


def test_learning_engine_validate_changes_returns_approval_state():
    engine = LearningEngineService()
    validation = engine.validate_changes([{"issue": "High error rate"}])

    assert validation["approved"] is True
    assert validation["status"] == "approved"
