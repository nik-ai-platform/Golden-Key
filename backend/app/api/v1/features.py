from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.services.feature_discovery_service import FeatureDiscoveryService
from app.services.feature_importance_service import FeatureImportanceService

router = APIRouter(
    prefix="/features",
    tags=["Features"],
    dependencies=[Depends(require_analyst)],
)


@router.get("/discovered")
def get_discovered_features():
    service = FeatureDiscoveryService()
    return service.discover_features("NBA")


@router.get("/{feature_id}")
def get_feature(feature_id: int):
    return {"id": feature_id, "feature_name": "Clutch Net Rating", "status": "UNDER_REVIEW"}


@router.post("/test")
def test_feature(payload: dict):
    discovery = FeatureDiscoveryService()
    importance = FeatureImportanceService()
    feature = payload.get("feature", {})
    return {
        "validation": discovery.validate_feature(feature),
        "impact": importance.build_report(feature),
    }


@router.get("/reports")
def get_reports():
    return {
        "sport": "NBA",
        "report": "Feature Discovery Report",
        "recommendation": "APPROVE",
    }
