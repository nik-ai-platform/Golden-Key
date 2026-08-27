from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.models.learning_event import LearningEvent
from app.models.model_performance import ModelPerformance
from app.services.adaptive_npi_optimizer_service import AdaptiveNPIOptimizerService
from app.services.feature_evolution_service import FeatureEvolutionService
from app.services.learning_engine_service import LearningEngineService
from app.services.market_regime_service import MarketRegimeService
from app.services.model_improvement_service import ModelImprovementService
from app.services.model_monitoring_service import ModelMonitoringService
from app.services.prediction_feedback_service import PredictionFeedbackService

router = APIRouter(prefix="/learning", tags=["Learning"], dependencies=[Depends(require_analyst)])

_LEARNING_EVENTS: list[dict] = []
_MODEL_PERFORMANCE: list[dict] = []


@router.post("/events")
def create_event(payload: dict):
    event = LearningEvent(
        model_name=payload.get("model_name", "NPI"),
        event_type=payload.get("event_type", "prediction_completed"),
        input_data=str(payload.get("input_data", {})),
        prediction=str(payload.get("prediction", "")),
        actual_result=str(payload.get("actual_result", "")),
        error_score=float(payload.get("error_score", 0.0) or 0.0),
    )
    record = {
        "id": len(_LEARNING_EVENTS) + 1,
        "model_name": event.model_name,
        "event_type": event.event_type,
        "input_data": event.input_data,
        "prediction": event.prediction,
        "actual_result": event.actual_result,
        "error_score": event.error_score,
    }
    _LEARNING_EVENTS.append(record)
    return record


@router.get("/performance")
def get_learning_performance():
    if not _MODEL_PERFORMANCE:
        _MODEL_PERFORMANCE.append({
            "model_name": "NPI NBA Model",
            "accuracy": 56.8,
            "ats_percentage": 56.8,
            "roi": 9.8,
            "calibration": 98.0,
            "confidence_error": 2.1,
            "recent_performance": "Last 30 Days: 49.2%",
            "historical_performance": "Season ATS: 56.8%",
            "status": "Needs Adjustment",
        })
    return _MODEL_PERFORMANCE


@router.get("/recommendations")
def get_learning_recommendations():
    engine = LearningEngineService()
    feedback = PredictionFeedbackService().process({"prediction": "Celtics cover"}, {"result": "Failed"})
    analysis = engine.analyze_results([feedback])
    improvements = engine.generate_improvements(analysis)
    feature_evolution = FeatureEvolutionService().evolve({"rest": 8})
    optimizer = AdaptiveNPIOptimizerService().optimize({"proposal": "Increase travel penalty: +2 points"})
    regime = MarketRegimeService().detect({"scoring": 212, "public_bias": True})
    monitoring = ModelMonitoringService().monitor({"prediction_accuracy": 51.0})
    recommendation = ModelImprovementService().recommend("Road teams undervalued")
    validation = engine.validate_changes(improvements)
    return {
        "analysis": analysis,
        "improvements": improvements,
        "feature_evolution": feature_evolution,
        "optimizer": optimizer,
        "regime": regime,
        "monitoring": monitoring,
        "recommendation": recommendation,
        "validation": validation,
    }
