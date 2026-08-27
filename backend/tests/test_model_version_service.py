from app.services.model_version_service import ModelVersionService


def setup_function(_function):
    ModelVersionService.CURRENT_VERSION = "NPI-v1"
    ModelVersionService.SPORT_VERSIONS = {}
    ModelVersionService.SPORT_VERSION_HISTORY = {}


def test_get_current_version_defaults_to_npi_v1():
    service = ModelVersionService()

    assert service.get_current_version() == "NPI-v1"


def test_set_current_version_updates_value():
    service = ModelVersionService()

    service.set_current_version("NPI-v2")

    assert service.get_current_version() == "NPI-v2"


def test_get_version_for_sport_falls_back_to_current_when_unset():
    service = ModelVersionService()

    assert service.get_version_for_sport("basketball_nba") == "NPI-v1"


def test_set_and_clear_version_for_sport():
    service = ModelVersionService()

    service.set_version_for_sport("basketball_nba", "NBA-v2")
    assert service.get_version_for_sport("basketball_nba") == "NBA-v2"

    service.clear_version_for_sport("basketball_nba")
    assert service.get_version_for_sport("basketball_nba") == "NPI-v1"


def test_rollback_version_for_sport_restores_previous_version():
    service = ModelVersionService()

    service.set_version_for_sport("basketball_nba", "NBA-v1")
    service.set_version_for_sport("basketball_nba", "NBA-v2")

    rolled_back = service.rollback_version_for_sport("basketball_nba")

    assert rolled_back == "NBA-v1"
    assert service.get_version_for_sport("basketball_nba") == "NBA-v1"
