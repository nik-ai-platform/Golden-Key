import app.services.prediction_service as prediction_service


def test_prediction_service_does_not_import_legacy_model():
    assert not hasattr(prediction_service, "NikScore")