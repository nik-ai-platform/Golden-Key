from types import SimpleNamespace

import pytest

from app.core.exceptions import PredictionException
from app.models.prediction.nba_model import NBAPredictionModel
from app.models.prediction.nfl_model import NFLPredictionModel
from app.models.prediction.registry import ModelRegistry
from app.models.prediction.wnba_model import WNBAPredictionModel


class _VersionedModel:
    def __init__(self, version):
        self.version = version

    def metadata(self):
        return {
            "model_name": "Test Model",
            "version": self.version,
            "supported_sport": "basketball_nba",
            "build_date": "2026-08-05",
        }


def _performance():
    return SimpleNamespace(
        wins=8,
        losses=2,
        offensive_rating=78.0,
        defensive_rating=65.0,
        recent_form=72.0,
    )


def _features():
    return {
        "offense": 70.0,
        "defense": 60.0,
        "form": 68.0,
        "win_rate": 72.0,
        "trend": 66.0,
        "scoring_average": 71.0,
        "defense_average": 62.0,
        "rest_days": 1.0,
    }


def test_registry_selects_model_for_supported_sports():
    registry = ModelRegistry()

    assert isinstance(registry.get_model("basketball_nba"), NBAPredictionModel)
    assert isinstance(registry.get_model("basketball_wnba"), WNBAPredictionModel)
    assert isinstance(registry.get_model("americanfootball_nfl"), NFLPredictionModel)


def test_registry_raises_for_unsupported_sport():
    registry = ModelRegistry()

    with pytest.raises(PredictionException):
        registry.get_model("soccer_epl")


def test_all_models_follow_same_prediction_interface():
    registry = ModelRegistry()
    home_perf = _performance()
    away_perf = _performance()
    home_features = _features()
    away_features = _features()

    for sport in ["basketball_nba", "basketball_wnba", "americanfootball_nfl"]:
        model = registry.get_model(sport)
        output = model.predict(
            home_team_name="Home Team",
            away_team_name="Away Team",
            home_performance=home_perf,
            away_performance=away_perf,
            home_features=home_features,
            away_features=away_features,
            analytics=None,
        )

        assert "home_score" in output
        assert "away_score" in output
        assert "recommendation" in output
        assert "confidence" in output
        assert "explanation" in output
        assert "metadata" in output

        metadata = output["metadata"]
        assert metadata["model_name"]
        assert metadata["version"]
        assert metadata["supported_sport"] == sport
        assert metadata["build_date"]


def test_registry_can_roll_forward_and_roll_back_active_version():
    registry = ModelRegistry(model_map={"basketball_nba": _VersionedModel("NBA-v1")})

    registry.register_version("basketball_nba", "NBA-v2", _VersionedModel("NBA-v2"))
    registry.set_active_version("basketball_nba", "NBA-v2")

    active = registry.get_model("basketball_nba")
    assert active.metadata()["version"] == "NBA-v2"
    assert registry.get_active_version("basketball_nba") == "nba-v2"

    registry.set_active_version("basketball_nba", "NBA-v1")

    rolled_back = registry.get_model("basketball_nba")
    assert rolled_back.metadata()["version"] == "NBA-v1"
    assert registry.get_active_version("basketball_nba") == "nba-v1"
