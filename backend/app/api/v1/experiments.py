from fastapi import APIRouter, Depends

from app.auth.dependencies import require_analyst
from app.services.experiment_runner_service import ExperimentRunnerService
from app.services.model_experiment_service import ModelExperimentService
from app.services.model_comparison_service import ModelComparisonService

router = APIRouter(
    prefix="/experiments",
    tags=["Experiments"],
    dependencies=[Depends(require_analyst)],
)


@router.post("")
def create_experiment(payload: dict):
    service = ModelExperimentService()
    return service.create_experiment(payload)


@router.get("")
def list_experiments():
    return [{"id": 1, "experiment_name": "NBA NPI Weight Test", "status": "COMPLETED"}]


@router.get("/{experiment_id}")
def get_experiment(experiment_id: int):
    return {"id": experiment_id, "status": "COMPLETED"}


@router.post("/{experiment_id}/run")
def run_experiment(experiment_id: int):
    service = ExperimentRunnerService()
    return service.run({"experiment_name": "NBA NPI Weight Test"})


@router.get("/models/recommendations")
def get_model_recommendations():
    service = ModelComparisonService()
    return service.compare({"roi": 3.2, "ats": 53.1, "calibration": 0.81}, {"roi": 5.1, "ats": 54.8, "calibration": 0.82})
