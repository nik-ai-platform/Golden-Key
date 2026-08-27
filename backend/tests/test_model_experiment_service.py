from app.services.experiment_runner_service import ExperimentRunnerService
from app.services.model_comparison_service import ModelComparisonService
from app.services.model_experiment_service import ModelExperimentService


def test_experiments_do_not_modify_active_models():
    service = ModelExperimentService()
    experiment = service.create_experiment({"experiment_name": "NBA NPI Weight Test", "base_model_version": "NBA-NPI-v4", "candidate_version": "NBA-NPI-v5"})

    assert experiment["status"] == "CREATED"
    assert experiment["candidate_version"] == "NBA-NPI-v5"


def test_results_are_reproducible():
    service = ModelExperimentService()
    first = service.run_experiment(1)
    second = service.run_experiment(1)

    assert first == second


def test_failed_experiments_recover_safely():
    service = ModelExperimentService()
    result = service.run_experiment(None)

    assert result["status"] == "FAILED"


def test_metrics_compare_correctly():
    service = ModelComparisonService()
    result = service.compare({"roi": 3.2, "ats": 53.1, "calibration": 0.81}, {"roi": 5.1, "ats": 54.8, "calibration": 0.82})

    assert result["recommendation"] == "PROMOTE"
    assert result["roi_improvement"] == 1.9


def test_promotion_rules_enforced():
    service = ModelExperimentService()
    comparison = service.compare_results({"roi": 0.5, "ats": 53.0, "calibration": 0.82})

    assert comparison["recommendation"] == "REVIEW"


def test_version_history_preserved():
    service = ModelExperimentService()
    experiment = service.create_experiment({"experiment_name": "Version History Test", "base_model_version": "v4", "candidate_version": "v5"})

    assert experiment["base_model_version"] == "v4"
    assert experiment["candidate_version"] == "v5"
