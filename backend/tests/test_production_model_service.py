from app.services.production_model_service import ProductionModelService


def test_production_service_exists():

    service = ProductionModelService()

    assert service is not None
