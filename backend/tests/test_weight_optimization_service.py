import pytest

from app.services.weight_optimization_service import WeightOptimizationService


def test_normalize_weights_totals_to_200():
    service = WeightOptimizationService()

    normalized = service.normalize_weights(
        {
            "momentum": 22,
            "rest": 12,
            "net_rating": 28,
            "pace": 18,
            "market": 20,
        }
    )

    assert round(sum(normalized.values()), 2) == 200.0


def test_sport_profiles_remain_isolated():
    service = WeightOptimizationService()

    service.set_active_profile(
        "nba",
        {
            "weights_json": {"momentum": 22, "rest": 12, "net_rating": 28, "pace": 18, "market": 20},
        },
    )
    service.set_active_profile(
        "nfl",
        {
            "weights_json": {
                "turnover_diff": 32,
                "qb_efficiency": 38,
                "pressure_rate": 24,
                "red_zone": 26,
                "market": 18,
            },
        },
    )

    nba_profile = service.get_active_profile("nba")
    nfl_profile = service.get_active_profile("nfl")

    assert "momentum" in nba_profile["weights_json"]
    assert "qb_efficiency" in nfl_profile["weights_json"]
    assert "qb_efficiency" not in nba_profile["weights_json"]


def test_candidate_profiles_do_not_overwrite_active_profile():
    service = WeightOptimizationService()

    active = {
        "weights_json": {
            "momentum": 22,
            "rest": 12,
            "net_rating": 28,
            "pace": 18,
            "market": 20,
        },
        "profile_name": "NBA-v3.2-active",
    }
    service.set_active_profile("nba", active)

    candidate = {
        "weights_json": service.generate_candidate_weights("nba"),
        "profile_name": "NBA-v3.3-candidate",
    }
    service.store_candidate_profile("nba", candidate)

    active_after = service.get_active_profile("nba")
    candidates = service.get_candidate_profiles("nba")

    assert active_after["profile_name"] == "NBA-v3.2-active"
    assert len(candidates) == 1
    assert candidates[0]["profile_name"] == "NBA-v3.3-candidate"


def test_profile_comparisons_are_repeatable():
    service = WeightOptimizationService()

    current = {
        "weights_json": {
            "momentum": 22,
            "rest": 12,
            "net_rating": 28,
            "pace": 18,
            "market": 20,
        },
        "metrics": {
            "accuracy": 54.3,
            "calibration": 7.2,
            "roi": 1.8,
        },
    }

    candidate = {
        "weights_json": service.generate_candidate_weights("nba"),
        "metrics": {
            "accuracy": 55.1,
            "calibration": 6.9,
            "roi": 2.0,
        },
    }

    first = service.compare_profiles(current, candidate)
    second = service.compare_profiles(current, candidate)

    assert first == second


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"momentum": None},
        {"momentum": -1},
        {"momentum": "bad"},
        {"momentum": 0, "rest": 0},
    ],
)
def test_invalid_weight_inputs_are_rejected(weights):
    service = WeightOptimizationService()

    with pytest.raises(ValueError):
        service.normalize_weights(weights)
