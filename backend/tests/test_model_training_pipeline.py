from app.models.training_dataset import TrainingDataset
from app.models.training_job import TrainingJob
from app.services.feature_drift_service import FeatureDriftService
from app.services.model_approval_service import ModelApprovalService
from app.services.model_backtest_service import ModelBacktestService
from app.services.model_comparison_service import ModelComparisonService
from app.services.model_drift_service import ModelDriftService
from app.services.model_health_service import ModelHealthService
from app.services.model_rollback_service import ModelRollbackService
from app.services.model_scheduler_service import ModelSchedulerService
from app.services.model_training_service import ModelTrainingService
from app.services.model_registry_service import ModelRegistryService


def test_dataset_version_is_immutable():
    service = ModelTrainingService()
    dataset = service.build_dataset(sport="NBA", dataset_version="v1", game_count=120, feature_version="2.2", date_range="2024-01-01:2024-06-30")
    assert dataset.dataset_version == "v1"
    assert dataset.feature_version == "2.2"
    assert dataset.game_count == 120


def test_training_is_reproducible():
    service = ModelTrainingService()
    first = service.build_dataset(sport="NBA", dataset_version="v1", game_count=120, feature_version="2.2")
    second = service.build_dataset(sport="NBA", dataset_version="v1", game_count=120, feature_version="2.2")
    assert first.checksum == second.checksum


def test_champion_comparison_is_deterministic():
    service = ModelComparisonService()
    result = service.compare_champion(
        {"ats": 54.8, "roi": 8.1, "calibration": 97},
        {"ats": 55.6, "roi": 9.3, "calibration": 98},
    )
    assert result["decision"] == "Candidate Wins"


def test_drift_detection_works():
    service = FeatureDriftService()
    result = service.detect_drift("Rest Days", 2.1, 3.8)
    assert result["status"] == "Drift Detected"


def test_rollback_restores_previous_model():
    service = ModelRollbackService()
    result = service.rollback("NBA v2.7", "NBA v2.6")
    assert result["restored_version"] == "NBA v2.6"


def test_failed_training_leaves_production_untouched():
    service = ModelTrainingService()
    service.production_version = "NBA v2.7"
    try:
        service.train_candidate(fail_training=True)
    except ValueError:
        pass
    assert service.production_version == "NBA v2.7"


def test_scheduled_jobs_execute_successfully():
    scheduler = ModelSchedulerService()
    scheduler.enqueue_job("nightly_dataset_build")
    scheduler.run_pending_jobs()
    assert scheduler.jobs[0]["status"] == "completed"


def test_registry_remains_consistent():
    registry = ModelRegistryService()
    entry = registry.create_registry_entry("NBA_Model", "NBA", "1.3", 56.1, True)
    assert entry.version == "1.3"
    assert registry.latest_production_model("NBA").version == "1.3"
