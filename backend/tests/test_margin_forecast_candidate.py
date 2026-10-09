from datetime import datetime, timedelta, timezone

import pytest

from app.services.margin_forecast_candidate import (
    ACTIVATION_ENABLED,
    MODEL_VERSION,
    forecast_home_margin_from_spread,
)
from app.services.margin_forecast_validation import (
    MarginForecastObservation,
    chronological_holdout,
    evaluate_chronological_holdout,
)


@pytest.mark.parametrize(
    ("spread_home", "expected_home_margin"),
    [
        (-3.5, 3.5),
        (3.5, -3.5),
        (-0.5, 0.5),
        (0.5, -0.5),
        (-21.5, 21.5),
        (21.5, -21.5),
        (0, 0),
    ],
)
def test_market_line_maps_to_home_margin_without_sign_inversion(
    spread_home: float,
    expected_home_margin: float,
) -> None:
    assert forecast_home_margin_from_spread(spread_home) == expected_home_margin


@pytest.mark.parametrize("spread_home", [None, True, float("nan"), float("inf"), "3.5"])
def test_invalid_market_lines_are_rejected(spread_home) -> None:
    with pytest.raises(ValueError, match="finite numeric line"):
        forecast_home_margin_from_spread(spread_home)


def test_candidate_is_explicitly_disabled_and_not_probability_model() -> None:
    assert MODEL_VERSION == "MARKET-MARGIN-CANDIDATE-1.0"
    assert ACTIVATION_ENABLED is False


def _observation(
    game_id: int,
    days: int,
    *,
    market_margin: float = 0.0,
    incumbent_margin: float | None = 0.0,
) -> MarginForecastObservation:
    return MarginForecastObservation(
        game_id=game_id,
        kickoff=datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=days),
        published_at=datetime(2026, 8, 31, tzinfo=timezone.utc) + timedelta(days=days),
        sport="NCAAF",
        model_version="NPI-4.0",
        actual_home_margin=1.0,
        market_implied_home_margin=market_margin,
        incumbent_home_margin=incumbent_margin,
    )


def test_chronological_holdout_keeps_later_games_out_of_history_prefix() -> None:
    observations = [_observation(game_id, day) for game_id, day in enumerate([4, 1, 5, 2, 3])]

    history, heldout = chronological_holdout(observations, holdout_fraction=0.4)

    assert [item.kickoff.day for item in history] == [2, 3, 4]
    assert [item.kickoff.day for item in heldout] == [5, 6]
    assert max(item.kickoff for item in history) < min(item.kickoff for item in heldout)


def test_single_observation_has_no_heldout_evaluation() -> None:
    history, heldout = chronological_holdout([_observation(1, 1)])

    assert len(history) == 1
    assert heldout == ()


@pytest.mark.parametrize("fraction", [0, 1, -0.2, 1.2, float("nan")])
def test_invalid_holdout_fraction_is_rejected(fraction: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        chronological_holdout([_observation(1, 1), _observation(2, 2)], fraction)


def test_heldout_metrics_compare_market_and_incumbent_on_later_games() -> None:
    observations = [
        _observation(1, 1),
        _observation(2, 2),
        _observation(3, 3, market_margin=2.0, incumbent_margin=-2.0),
        _observation(4, 4, market_margin=2.0, incumbent_margin=None),
    ]

    result = evaluate_chronological_holdout(observations, holdout_fraction=0.5)

    assert result["history_prefix_games"] == 2
    assert result["heldout_games"] == 2
    assert result["market_candidate"] == {
        "sample_size": 2,
        "mae": 1.0,
        "rmse": 1.0,
        "mean_error": 1.0,
    }
    assert result["incumbent_npi_margin"] == {
        "sample_size": 1,
        "mae": 3.0,
        "rmse": 3.0,
        "mean_error": -3.0,
    }
