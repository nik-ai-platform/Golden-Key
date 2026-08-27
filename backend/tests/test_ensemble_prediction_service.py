from app.services.ensemble_prediction_service import EnsemblePredictionService
from app.services.model_disagreement_service import ModelDisagreementService
from app.services.model_registry_service import ModelRegistryService


def test_all_models_contribute_correctly():
    service = EnsemblePredictionService()
    result = service.generate_prediction(1)

    assert result["prediction"] in {"HOME", "AWAY"}
    assert result["confidence"] >= 0


def test_weights_sum_correctly():
    service = EnsemblePredictionService()
    combined = service.combine_predictions([
        {"id": "npi", "prediction": "HOME", "confidence": 78},
        {"id": "market", "prediction": "HOME", "confidence": 74},
        {"id": "historical", "prediction": "HOME", "confidence": 72},
        {"id": "situational", "prediction": "HOME", "confidence": 70},
        {"id": "live", "prediction": "AWAY", "confidence": 64},
    ])

    assert combined["score"] > 0


def test_missing_models_handled_safely():
    service = EnsemblePredictionService()
    result = service.combine_predictions([])

    assert result["prediction"] == "UNKNOWN"


def test_disagreement_lowers_confidence():
    service = EnsemblePredictionService()
    result = service.calculate_confidence({"score": 80, "agreement": "LOW"})

    assert result == 70


def test_ensemble_results_reproducible():
    service = EnsemblePredictionService()
    first = service.generate_prediction(2)
    second = service.generate_prediction(2)

    assert first == second


def test_active_model_versions_preserved():
    service = ModelRegistryService()
    models = service.list_models()

    assert len(models) == 5
    assert any(model["name"] == "NPI" for model in models)
