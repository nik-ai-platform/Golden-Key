from app.services.model_bootstrap_service import ModelBootstrapService


def test_baseline_weights_total_200():
    service = ModelBootstrapService()

    assert sum(service.BASELINE_WEIGHTS.values()) == 200


def test_supported_sports():
    service = ModelBootstrapService()

    assert set(service.SPORTS) == {
        "NFL",
        "NBA",
        "NCAAF",
        "NCAAB",
        "WNBA",
    }
