from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.services.error_analysis_service import ErrorAnalysisService
from app.services.learning_feedback_service import LearningFeedbackService
from app.services.model_performance_service import ModelPerformanceService
from app.services.outcome_tracking_service import OutcomeTrackingService

router = APIRouter(
    prefix="/performance",
    tags=["Performance"],
    dependencies=[Depends(require_analyst)],
)


@router.get("/models")
def get_models():
    service = ModelPerformanceService()
    return service.summarize({"overall_accuracy": 0.54, "ats": 54.2, "roi": 4.8, "confidence_calibration": 0.82})


@router.get("/errors")
def get_errors():
    service = ErrorAnalysisService()
    return service.classify_error("MODEL_ERROR")


@router.get("/recommendations")
def get_recommendations():
    service = LearningFeedbackService()
    return service.suggest_improvement("Favorite > 10 points")


@router.post("/result")
def post_result(payload: dict):
    service = OutcomeTrackingService()
    return service.record_result(payload)
