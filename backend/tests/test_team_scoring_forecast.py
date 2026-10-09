from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from app.services.team_scoring_evaluation import (
    ScoringForecastCase,
    cover_outcome,
    devigged_home_probability,
    evaluate_forecasts,
    select_positive_ev_side,
    settled_unit_profit,
)
from app.services.team_scoring_forecast import (
    ACTIVATION_ENABLED,
    MIN_CALIBRATION_ERRORS,
    MODEL_VERSION,
    TimestampedScore,
    available_scores_as_of,
    estimate_cover_probabilities,
    forecast_home_margin,
)
from app.services.team_scoring_walkforward import (
    GamePeriod,
    split_games_chronologically,
)


AS_OF = datetime(2026, 10, 1, tzinfo=UTC)


def _score(
    game_id: int,
    home: int,
    away: int,
    day: int,
    home_score: float,
    away_score: float,
    *,
    received_days_later: int = 0,
    neutral: bool = True,
    status: str = "final",
    observation_id: int | None = None,
) -> TimestampedScore:
    kickoff = AS_OF - timedelta(days=day)
    return TimestampedScore(
        game_id=game_id,
        sport="NFL",
        home_team_id=home,
        away_team_id=away,
        kickoff=kickoff,
        observed_at=kickoff + timedelta(days=received_days_later, hours=3),
        neutral_site=neutral,
        home_score=home_score,
        away_score=away_score,
        status=status,
        observation_id=observation_id if observation_id is not None else game_id,
    )


def _synthetic_history() -> tuple[TimestampedScore, ...]:
    offense = {1: 9.0, 2: 2.0, 3: -3.0, 4: -8.0}
    defense_allowed = {1: -4.0, 2: -1.0, 3: 2.0, 4: 5.0}
    games = []
    pairs = [(1, 2), (2, 3), (3, 4), (4, 1), (1, 3), (2, 4)]
    for day, (home, away) in enumerate(pairs * 3, start=2):
        home_field = 2.5
        home_points = 21 + offense[home] + defense_allowed[away] + home_field
        away_points = 21 + offense[away] + defense_allowed[home]
        games.append(
            _score(
                day,
                home,
                away,
                day,
                home_points,
                away_points,
                neutral=False,
            )
        )
    return tuple(games)


def test_candidate_is_versioned_disabled_and_not_connected_to_predictions() -> None:
    assert MODEL_VERSION == "TEAM-SCORING-RIDGE-1.0"
    assert ACTIVATION_ENABLED is False
    assert callable(forecast_home_margin)


def test_actual_receipt_time_is_strict_and_later_corrections_do_not_leak() -> None:
    early = _score(1, 1, 2, 5, 10, 7, received_days_later=0, observation_id=1)
    correction = TimestampedScore(
        **{
            **early.__dict__,
            "home_score": 21,
            "observed_at": AS_OF - timedelta(hours=1),
            "observation_id": 2,
        }
    )
    exactly_at_cutoff = _score(3, 3, 4, 4, 14, 7)
    exactly_at_cutoff = TimestampedScore(
        **{**exactly_at_cutoff.__dict__, "observed_at": AS_OF, "observation_id": 3}
    )

    available = available_scores_as_of(
        (early, correction, exactly_at_cutoff),
        sport="NFL",
        as_of=AS_OF,
        exclude_game_id=99,
    )

    assert [(item.game_id, item.home_score) for item in available] == [(1, 21)]


def test_later_invalid_revision_invalidates_old_final_as_of_that_time() -> None:
    final = _score(1, 1, 2, 5, 10, 7, observation_id=1)
    void = TimestampedScore(
        **{
            **final.__dict__,
            "status": "canceled",
            "observed_at": final.observed_at + timedelta(hours=1),
            "observation_id": 2,
        }
    )
    assert available_scores_as_of(
        (final, void),
        sport="NFL",
        as_of=AS_OF,
        exclude_game_id=99,
    ) == ()


def test_forecast_uses_team_scoring_and_opponent_strength_with_sign_symmetry() -> None:
    history = _synthetic_history()
    original = tuple(history)
    forward = forecast_home_margin(
        history,
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=True,
        as_of=AS_OF,
        target_game_id=999,
    )
    reverse = forecast_home_margin(
        history,
        sport="NFL",
        home_team_id=4,
        away_team_id=1,
        neutral_site=True,
        as_of=AS_OF,
        target_game_id=999,
    )

    assert forward is not None and reverse is not None
    assert forward.home_margin > 0
    assert reverse.home_margin == pytest.approx(-forward.home_margin, abs=1e-9)
    assert len(history) == len(original)
    assert history == original
    with pytest.raises(FrozenInstanceError):
        history[0].home_score = 0


def test_home_advantage_applies_once_and_neutral_sites_have_no_home_boost() -> None:
    history = _synthetic_history()
    neutral = forecast_home_margin(
        history,
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=True,
        as_of=AS_OF,
        target_game_id=999,
    )
    home = forecast_home_margin(
        history,
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=False,
        as_of=AS_OF,
        target_game_id=999,
    )

    assert neutral is not None and home is not None
    assert home.home_margin > neutral.home_margin
    assert home.home_margin - neutral.home_margin < 5


def test_target_result_and_same_timestamp_score_are_not_used_for_its_forecast() -> None:
    history = list(_synthetic_history())
    target_result = _score(999, 1, 4, 1, 100, 0)
    not_received_yet = _score(1000, 1, 4, 1, 100, 0)
    not_received_yet = TimestampedScore(
        **{**not_received_yet.__dict__, "observed_at": AS_OF}
    )
    baseline = forecast_home_margin(
        history,
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=True,
        as_of=AS_OF,
        target_game_id=999,
    )
    with_future = forecast_home_margin(
        history + [target_result, not_received_yet],
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=True,
        as_of=AS_OF,
        target_game_id=999,
    )

    assert baseline is not None and with_future is not None
    assert with_future.home_margin == pytest.approx(baseline.home_margin)


def test_sparse_or_unknown_neutral_site_history_is_unavailable() -> None:
    sparse = _synthetic_history()[:4]
    assert forecast_home_margin(
        sparse,
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=True,
        as_of=AS_OF,
        target_game_id=999,
    ) is None
    assert forecast_home_margin(
        _synthetic_history(),
        sport="NFL",
        home_team_id=1,
        away_team_id=4,
        neutral_site=None,
        as_of=AS_OF,
        target_game_id=999,
    ) is None


def test_half_point_and_whole_point_spread_signs_and_pushes_are_separate() -> None:
    assert cover_outcome(3, -2.5, "HOME") == "WIN"
    assert cover_outcome(3, -3.5, "HOME") == "LOSS"
    assert cover_outcome(-4, 3.5, "AWAY") == "WIN"
    assert cover_outcome(3, -3, "HOME") == "PUSH"
    assert cover_outcome(3, -3, "AWAY") == "PUSH"

    outcomes = estimate_cover_probabilities(
        forecast_home_margin=0,
        spread_home=0,
        earlier_forecast_errors=(-1, 0, 1) * 10,
    )
    assert outcomes is not None
    assert outcomes.home_cover == pytest.approx(1 / 3)
    assert outcomes.away_cover == pytest.approx(1 / 3)
    assert outcomes.push == pytest.approx(1 / 3)


def test_cover_probability_requires_earlier_validation_sample() -> None:
    assert MIN_CALIBRATION_ERRORS == 30
    assert estimate_cover_probabilities(
        forecast_home_margin=2,
        spread_home=-1,
        earlier_forecast_errors=(0.0,) * 29,
    ) is None


def test_prices_require_a_paired_line_and_are_not_imputed() -> None:
    assert devigged_home_probability(-3.5, 3.5, -110, -110) == pytest.approx(0.5)
    assert devigged_home_probability(-3.5, 3, -110, -110) is None
    assert devigged_home_probability(-3.5, 3.5, -110, None) is None


def test_actual_price_roi_handles_pushes_and_positive_ev_selection() -> None:
    probabilities = estimate_cover_probabilities(
        forecast_home_margin=0,
        spread_home=-1,
        earlier_forecast_errors=(2.0,) * 30,
    )
    assert probabilities is not None
    assert select_positive_ev_side(probabilities, -110, -110) == ("HOME", pytest.approx(100 / 110))
    assert settled_unit_profit(
        selected_side="HOME",
        outcome="PUSH",
        american_price=-110,
    ) == 0
    assert settled_unit_profit(
        selected_side="HOME",
        outcome="WIN",
        american_price=130,
    ) == pytest.approx(1.3)


def test_game_split_is_chronological_and_never_splits_duplicate_versions() -> None:
    games = [
        GamePeriod(game_id, AS_OF + timedelta(days=game_id))
        for game_id in range(1, 11)
    ]
    games.extend(
        [
            GamePeriod(3, AS_OF + timedelta(days=3)),
            GamePeriod(8, AS_OF + timedelta(days=8)),
        ]
    )

    periods = split_games_chronologically(games)

    sets = [set(periods[name]) for name in ("training", "tuning", "final_test")]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert sorted(set.union(*sets)) == list(range(1, 11))
    assert len(periods["training"]) == 6


def test_evaluator_distinguishes_prices_probabilities_and_pushes() -> None:
    case = ScoringForecastCase(
        game_id=1,
        sport="NFL",
        model_version="NPI-5.0",
        kickoff_sort=1.0,
        published_sort=0.0,
        actual_home_margin=3,
        spread_home=-3,
        spread_away=3,
        selection="HOME",
        spread_home_price=-105,
        spread_away_price=-115,
        published_selection_price=-105,
        candidate_home_margin=2.0,
        incumbent_home_margin=1.0,
        calibration_errors=(2.0,) * 30,
        incumbent_calibration_errors=(2.0,) * 30,
    )

    report = evaluate_forecasts([case])

    assert report["coverage"]["candidate_margin_available"] == 1
    assert report["coverage"]["paired_market_prices"] == 1
    assert report["candidate_cover_probability"]["sample_size"] == 0
    assert report["devigged_market_cover_probability"]["sample_size"] == 0
    assert report["published_npi_pick_actual_price_roi"]["sample_size"] == 1
    assert report["published_npi_pick_actual_price_roi"]["units_profit"] == 0
