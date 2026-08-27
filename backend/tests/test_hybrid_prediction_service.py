from app.models.ml_feature import MLFeature
from app.models.model_registry import ModelRegistry
from app.services.calibration_service import CalibrationService
from app.services.explainability_service import ExplainabilityService
from app.services.hybrid_prediction_service import HybridPredictionService
from app.services.ml_feature_service import MLFeatureService


def test_feature_generation_is_stable():
    service = MLFeatureService()
    features = service.build_features({
        "game_id": 101,
        "sport": "NBA",
        "home_team": "Boston",
        "away_team": "Miami",
        "rest_days": 3,
        "weather": "clear",
        "market": "spread",
        "injury": "none",
        "travel": 1,
        "schedule": "back_to_back",
        "coach": "recent",
    })
    assert features[0]["feature_name"] == "rest_days"
    assert features[0]["feature_value"] == 3


def test_training_dataset_is_reproducible():
    service = MLFeatureService()
    dataset = service.export_training_dataset("NBA")
    assert dataset == service.export_training_dataset("NBA")


def test_registry_versioning_works():
    registry = ModelRegistry(model_name="NBA_Model_v1.3", sport="NBA", version="1.3", validation_score=56.1, production_status=True)
    assert registry.version == "1.3"
    assert registry.production_status is True


def test_hybrid_predictions_are_deterministic():
    service = HybridPredictionService()
    result = service.combine_predictions(81, 76)
    assert result["combined_probability"] == 79.0
    assert result["agreement"] == "high"


def test_calibration_improves_probability_accuracy():
    service = CalibrationService()
    calibrated = service.calibrate_probability(0.76, reliability=0.98, calibration_error=0.03)
    assert calibrated == 0.75


def test_explainability_is_always_available():
    service = ExplainabilityService()
    explanation = service.explain_prediction("Boston -5", 82, ["Rest Advantage", "Home Court"], ["Injury uncertainty"])
    assert explanation["confidence"] == 82
    assert "Rest Advantage" in explanation["top_factors"]


def test_npi_output_is_unchanged_by_ml_failures():
    service = HybridPredictionService()
    result = service.combine_predictions(81, None)
    assert result["final_confidence"] == 81
    assert result["source"] == "npi_only"
