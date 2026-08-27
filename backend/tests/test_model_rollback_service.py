from app.services.model_rollback_service import ModelRollbackService


def test_rollback_service_exists():

    service = ModelRollbackService()

    assert service is not None
