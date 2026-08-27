from datetime import datetime
from datetime import UTC

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst
from app.auth.dependencies import require_admin
from app.core.exceptions import PredictionException
from app.database.session import get_db
from app.models.model_performance import ModelPerformance
from app.models.weight_profile import WeightProfile
from app.services.calibration_service import CalibrationService
from app.services.explainability_service import ExplainabilityService
from app.services.feature_drift_service import FeatureDriftService
from app.services.hybrid_prediction_service import HybridPredictionService
from app.services.ml_feature_service import MLFeatureService
from app.services.model_approval_service import ModelApprovalService
from app.services.model_backtest_service import ModelBacktestService
from app.services.model_comparison_service import ModelComparisonService
from app.services.model_drift_service import ModelDriftService
from app.services.model_evaluation_service import ModelEvaluationService
from app.services.model_health_service import ModelHealthService
from app.services.model_monitoring_service import ModelMonitoringService
from app.services.model_improvement_service import ModelImprovementService
from app.services.model_registry_service import ModelRegistryService
from app.services.model_rollback_service import ModelRollbackService
from app.services.model_scheduler_service import ModelSchedulerService
from app.services.model_training_service import ModelTrainingService
from app.services.model_version_service import ModelVersionService
from app.services.neural_prediction_service import NeuralPredictionService
from app.services.weight_optimization_service import WeightOptimizationService
from app.models.model_version import ModelVersion


router = APIRouter(
    prefix="/models",
    tags=["Models"],
    dependencies=[Depends(require_analyst)],
)


class CompareModelsRequest(BaseModel):
    current_version: str
    candidate_version: str
    games: list[dict] = []


class ActiveVersionRequest(BaseModel):
    sport: str
    action: str
    version: str | None = None


class WeightOptimizeRequest(BaseModel):
    sport: str
    model_version: str
    profile_name: str | None = None
    base_weights: dict[str, float] | None = None
    current_metrics: dict[str, float] | None = None
    candidate_metrics: dict[str, float] | None = None


class PredictModelRequest(BaseModel):
    game: dict | None = None
    npi_score: float | None = None
    ml_prediction: float | None = None


class ModelVersionRequest(BaseModel):
    model_name: str
    version: str
    sport: str = "general"
    changes: str | None = None
    performance: str | None = None
    status: str = "Testing"
    approved_by: str | None = None


def _prediction_runtime_service():
    from app.api.v1 import predictions as predictions_router

    return predictions_router.service


def _registry_row(record):
    return {
        "model_version": record.model_version,
        "release_date": None,
        "feature_set": [],
        "evaluation_metrics": {
            "accuracy": round(float(record.accuracy or 0.0), 2),
            "calibration": 0.0,
            "average_confidence": round(float(record.average_confidence or 0.0), 2),
            "predictions": int(record.total_predictions or 0),
        },
        "deployment_status": "active",
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


def _weight_profile_row(record: WeightProfile):
    return {
        "id": record.id,
        "sport": record.sport,
        "model_version": record.model_version,
        "profile_name": record.profile_name,
        "weights_json": record.weights_json,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "is_active": bool(record.is_active),
    }


@router.get("")
def list_models(db: Session = Depends(get_db)):
    rows = db.query(ModelPerformance).order_by(ModelPerformance.model_version.asc()).all()
    return [_registry_row(row) for row in rows]


@router.get("/weights")
def list_weight_profiles(
    sport: str | None = None,
    model_version: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(WeightProfile)

    if sport:
        query = query.filter(WeightProfile.sport == sport)

    if model_version:
        query = query.filter(WeightProfile.model_version == model_version)

    rows = query.order_by(WeightProfile.created_at.desc(), WeightProfile.id.desc()).all()
    return [_weight_profile_row(row) for row in rows]


@router.get("/weights/{version}")
def get_weight_profiles_for_version(
    version: str,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(WeightProfile)
        .filter(WeightProfile.model_version == version)
        .order_by(WeightProfile.created_at.desc(), WeightProfile.id.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Weight profiles not found for model version")

    return [_weight_profile_row(row) for row in rows]


@router.post("/weights/optimize")
def optimize_weight_profile(
    payload: WeightOptimizeRequest,
    db: Session = Depends(get_db),
):
    optimizer = WeightOptimizationService()

    active = (
        db.query(WeightProfile)
        .filter(WeightProfile.sport == payload.sport)
        .filter(WeightProfile.model_version == payload.model_version)
        .filter(WeightProfile.is_active.is_(True))
        .order_by(WeightProfile.created_at.desc(), WeightProfile.id.desc())
        .first()
    )

    if payload.base_weights is not None:
        base_weights = payload.base_weights
    elif active is not None:
        base_weights = active.weights_json
    else:
        base_weights = optimizer.SPORT_BASELINES.get(
            (payload.sport or "").strip().lower(),
            optimizer.SPORT_BASELINES["nba"],
        )

    candidate_weights = optimizer.generate_candidate_weights(payload.sport)

    comparison = optimizer.compare_profiles(
        {
            "weights_json": base_weights,
            "metrics": payload.current_metrics or {},
        },
        {
            "weights_json": candidate_weights,
            "metrics": payload.candidate_metrics or {},
        },
    )

    recommendation = optimizer.recommend_profile(comparison)

    profile = WeightProfile(
        sport=payload.sport,
        model_version=payload.model_version,
        profile_name=payload.profile_name or f"{payload.sport}-candidate",
        weights_json=candidate_weights,
        is_active=False,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "candidate_profile": _weight_profile_row(profile),
        "comparison": comparison,
        "recommendation": recommendation,
    }


@router.get("/status")
def get_model_status():
    return {
        "status": "production",
        "model_version": "1.3",
        "validation_score": 56.1,
        "calibration": 98.0,
        "prediction_agreement": 91.0,
        "health": "excellent",
    }


@router.get("/performance")
def get_model_performance():
    monitoring_service = ModelMonitoringService()
    return monitoring_service.performance_dashboard()


@router.post("/train")
def train_model():
    training_service = ModelTrainingService()
    dataset = training_service.build_dataset()
    training_service.train_candidate(dataset=dataset)
    return {"dataset_version": dataset.dataset_version, "status": "queued"}


@router.get("/jobs")
def list_training_jobs():
    return [{"model_version": "NBA v2.7", "status": "APPROVED"}]


@router.get("/drift")
def get_model_drift():
    drift_service = FeatureDriftService()
    return drift_service.detect_drift("Rest Days", 2.1, 3.8)


@router.get("/champion")
def get_champion_model():
    return {"champion": "NBA v2.7", "status": "production"}


@router.post("/promote/legacy", deprecated=True)
def promote_model_legacy():
    approval_service = ModelApprovalService()
    return approval_service.promote({}, manual_approval=True)


@router.post("/rollback")
def rollback_model():
    rollback_service = ModelRollbackService()
    return rollback_service.rollback("NBA v2.7", "NBA v2.6")


@router.post("/predict")
def predict_model(payload: PredictModelRequest):
    feature_service = MLFeatureService()
    neural_service = NeuralPredictionService()
    hybrid_service = HybridPredictionService()
    calibration_service = CalibrationService()

    features = feature_service.build_features(payload.game)
    neural_result = neural_service.predict(features)

    ml_prediction = payload.ml_prediction if payload.ml_prediction is not None else neural_result["confidence"]
    hybrid_result = hybrid_service.combine_predictions(payload.npi_score, ml_prediction)
    calibrated = calibration_service.calibrate_probability(
        hybrid_result["final_confidence"] / 100.0,
        reliability=0.98,
        calibration_error=0.03,
    )

    return {
        "prediction": hybrid_result,
        "calibrated_probability": round(calibrated * 100.0, 2),
        "model_backend": neural_result["backend"],
    }


@router.get("/explain/{game_id}")
def explain_model(game_id: int):
    explanation_service = ExplainabilityService()
    return explanation_service.explain_prediction(
        "Boston -5",
        82,
        ["Rest Advantage", "Home Court", "Defensive Rating"],
        ["Injury uncertainty"],
        game_id=game_id,
    )


@router.get("/versions")
def list_versions(db: Session = Depends(get_db)):
    rows = db.query(ModelVersion).order_by(ModelVersion.created_at.desc(), ModelVersion.id.desc()).all()
    return [
        {
            "id": row.id,
            "model_name": row.model_name,
            "version": row.version,
            "changes": row.changes,
            "performance": row.performance,
            "status": row.status,
            "approved_by": row.approved_by,
        }
        for row in rows
    ]


@router.post("/versions")
def create_version(payload: ModelVersionRequest, db: Session = Depends(get_db)):
    row = ModelVersion(
        model_name=payload.model_name,
        version=payload.version,
        sport=payload.sport,
        changes=payload.changes,
        performance=payload.performance,
        status=payload.status,
        approved_by=payload.approved_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "model_name": row.model_name,
        "version": row.version,
        "changes": row.changes,
        "performance": row.performance,
        "status": row.status,
        "approved_by": row.approved_by,
    }


@router.post("/approve")
def approve_model_version(payload: dict):
    service = ModelApprovalService()
    improvement = ModelImprovementService().recommend(payload.get("issue", "Road teams undervalued"))
    approval = service.promote({}, manual_approval=payload.get("manual_approval", True))
    return {"approval": approval, "improvement": improvement}


@router.get("/{version}")
def get_model(version: str, db: Session = Depends(get_db)):
    row = (
        db.query(ModelPerformance)
        .filter(ModelPerformance.model_version == version)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Model version not found")

    return _registry_row(row)


@router.post("/compare")
def compare_models(payload: CompareModelsRequest, db: Session = Depends(get_db)):
    service = ModelEvaluationService()

    if payload.games:
        current_metric = service.evaluate_model(payload.current_version, payload.games)
        candidate_metric = service.evaluate_model(payload.candidate_version, payload.games)
        return service.compare_models(current_metric, candidate_metric)

    current = (
        db.query(ModelPerformance)
        .filter(ModelPerformance.model_version == payload.current_version)
        .first()
    )
    candidate = (
        db.query(ModelPerformance)
        .filter(ModelPerformance.model_version == payload.candidate_version)
        .first()
    )

    if not current or not candidate:
        raise HTTPException(status_code=404, detail="One or both model versions not found")

    current_metric = {
        "accuracy": round(float(current.accuracy or 0.0), 2),
        "calibration": 0.0,
        "average_confidence": round(float(current.average_confidence or 0.0), 2),
        "predictions": int(current.total_predictions or 0),
    }
    candidate_metric = {
        "accuracy": round(float(candidate.accuracy or 0.0), 2),
        "calibration": 0.0,
        "average_confidence": round(float(candidate.average_confidence or 0.0), 2),
        "predictions": int(candidate.total_predictions or 0),
    }

    return service.compare_models(current_metric, candidate_metric)


@router.get("/active-version")
def get_active_version(
    sport: str,
    _admin=Depends(require_admin),
):
    runtime_service = _prediction_runtime_service()

    try:
        active_version = runtime_service.model_registry.get_active_version(sport)
        versions = runtime_service.model_registry.list_versions(sport)
    except PredictionException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    configured_version = runtime_service.version_service.get_version_for_sport(
        sport,
        default=None,
    )

    return {
        "sport": sport,
        "active_version": active_version,
        "configured_version": configured_version,
        "available_versions": versions,
    }


@router.post("/active-version")
def mutate_active_version(
    payload: ActiveVersionRequest,
    _admin=Depends(require_admin),
):
    action = (payload.action or "").strip().lower()
    if action not in {"promote", "rollback"}:
        raise HTTPException(
            status_code=400,
            detail="Action must be one of: promote, rollback",
        )

    runtime_service = _prediction_runtime_service()
    version_service = runtime_service.version_service or ModelVersionService()
    registry = runtime_service.model_registry

    try:
        if action == "promote":
            if not payload.version:
                raise HTTPException(
                    status_code=400,
                    detail="version is required when action is promote",
                )
            target_version = payload.version
            registry.set_active_version(payload.sport, target_version)
            version_service.set_version_for_sport(payload.sport, target_version)
        else:
            if payload.version:
                target_version = payload.version
                registry.set_active_version(payload.sport, target_version)
                version_service.set_version_for_sport(payload.sport, target_version)
            else:
                target_version = version_service.rollback_version_for_sport(payload.sport)
                registry.set_active_version(payload.sport, target_version)
    except PredictionException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "sport": payload.sport,
        "action": action,
        "active_version": registry.get_active_version(payload.sport),
        "available_versions": registry.list_versions(payload.sport),
    }