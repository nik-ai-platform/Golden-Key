from app.services.validation_service import (
    ValidationService
)


def test_score_validation():

    service = ValidationService()

    assert service.validate_score(
        50
    )

    assert not service.validate_score(
        None
    )
