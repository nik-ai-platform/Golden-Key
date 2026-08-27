from app.services.model_weight_service import (
    ModelWeightService
)


def test_default_weights():

    service = ModelWeightService()

    weights = service.get_weights()

    assert (
        weights["strength"]
        ==
        0.40
    )
