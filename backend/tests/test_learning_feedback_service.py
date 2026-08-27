from app.services.error_analysis_service import ErrorAnalysisService
from app.services.learning_feedback_service import LearningFeedbackService
from app.services.model_performance_service import ModelPerformanceService
from app.services.outcome_tracking_service import OutcomeTrackingService
from app.services.prediction_evaluation_service import PredictionEvaluationService


def test_predictions_stored_correctly():
    service = OutcomeTrackingService()
    result = service.record_result({"status": "COMPLETED", "result": "KC"})

    assert result["status"] == "COMPLETED"


def test_results_update_properly():
    service = OutcomeTrackingService()
    result = service.update_prediction(2)

    assert result["status"] == "UPDATED"


def test_errors_classified_correctly():
    service = ErrorAnalysisService()
    result = service.classify_error("MODEL_ERROR")

    assert result["classification"] == "MODEL_ERROR"


def test_performance_metrics_calculate_correctly():
    service = ModelPerformanceService()
    result = service.summarize({"overall_accuracy": 0.54, "ats": 54.2, "roi": 4.8, "confidence_calibration": 0.82})

    assert result["ats"] == 54.2


def test_learning_suggestions_do_not_modify_production():
    service = LearningFeedbackService()
    result = service.suggest_improvement("Favorite > 10 points")

    assert result["recommendation"] == "Reduce favorite confidence weighting"


def test_model_history_preserved():
    service = PredictionEvaluationService()
    result = service.evaluate({"prediction": "DAL", "confidence": 84}, {"result": "DAL", "score": 1})

    assert result["ats_result"] == "WIN"
