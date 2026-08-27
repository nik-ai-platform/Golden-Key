from fastapi import APIRouter, Depends

from app.auth.dependencies import require_viewer
from app.services.ensemble_prediction_service import EnsemblePredictionService
from app.services.model_disagreement_service import ModelDisagreementService
from app.services.model_registry_service import ModelRegistryService

router = APIRouter(
    prefix="/ensemble",
    tags=["Ensemble"],
    dependencies=[Depends(require_viewer)],
)


@router.get("/{game_id}")
def get_ensemble_prediction(game_id: int):
    service = EnsemblePredictionService()
    return service.generate_prediction(game_id)


@router.get("/models")
def get_models():
    service = ModelRegistryService()
    return service.list_models()


@router.get("/disagreements")
def get_disagreements():
    service = ModelDisagreementService()
    return service.assess([
        {"prediction": "BOS"},
        {"prediction": "MIA"},
    ])
