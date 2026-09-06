from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.nik_score import NikScore
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.services.ncaaf_power_rating_service import (
    MODEL_VERSION,
    PROVISIONAL_HOME_FIELD_POINTS,
    TeamPowerRating,
    calculate_rating_result,
    calculate_team_ratings,
    get_expected_home_margin,
    recency_weight,
    transform_margin,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _team(db, name):
    team = Team(name=name, sport="NCAAF", league="NCAAF")
    db.add(team)
    db.flush()
    return team


def _final_game(
    db,
    home,
    away,
    kickoff,
    home_score,
    away_score,
    *,
    neutral=True,
    observed_at=None,
    season=2025,
):
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=season,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        home_score=home_score,
        away_score=away_score,
        status="final",
        neutral_site=neutral,
    )
    db.add(game)
    db.flush()
    if observed_at is not None:
        db.add(
            GameResultObservation(
                game_id=game.id,
                provider="cfbd",
                home_score=home_score,
                away_score=away_score,
                status="final",
                observed_at=observed_at.replace(tzinfo=None),
            )
        )
    db.flush()
    return game


def test_transform_margin_is_symmetric_linear_then_compressed():
    assert transform_margin(0) == 0
    assert transform_margin(21) == 21
    assert transform_margin(-21) == -21
    assert transform_margin(-50) == pytest.approx(-transform_margin(50))
    assert 21 < transform_margin(50) < 50


def test_recency_weight_and_timestamp_contract():
    as_of = datetime(2025, 12, 1, tzinfo=UTC)
    assert recency_weight(as_of, as_of) == 1.0
    assert recency_weight(as_of - timedelta(days=56), as_of) == pytest.approx(0.5)
    assert recency_weight(as_of - timedelta(days=112), as_of) == pytest.approx(0.25)
    with pytest.raises(ValueError):
        recency_weight(as_of + timedelta(seconds=1), as_of)
    with pytest.raises(ValueError):
        recency_weight(as_of.replace(tzinfo=None), as_of)


def test_two_team_neutral_and_home_margin_conventions(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(db, home, away, kickoff, 31, 21, neutral=True, observed_at=kickoff + timedelta(hours=6))
    neutral = calculate_team_ratings(db, kickoff + timedelta(days=1), 2025)

    assert neutral[home.id].rating > neutral[away.id].rating
    assert sum(item.rating * (item.effective_games + 4) for item in neutral.values()) == pytest.approx(0)
    assert get_expected_home_margin(neutral[home.id], neutral[away.id], True) == pytest.approx(
        neutral[home.id].rating - neutral[away.id].rating
    )
    assert get_expected_home_margin(neutral[home.id], neutral[away.id], False) == pytest.approx(
        neutral[home.id].rating - neutral[away.id].rating + PROVISIONAL_HOME_FIELD_POINTS
    )


def test_ratings_accept_stable_game_observation_without_team_season_metadata(db):
    home = _team(db, "Metadata Missing Home")
    away = _team(db, "Metadata Missing Away")
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(
        db,
        home,
        away,
        kickoff,
        24,
        17,
        neutral=False,
        observed_at=kickoff + timedelta(hours=6),
    )

    ratings = calculate_team_ratings(db, kickoff + timedelta(days=1), 2025)

    assert set(ratings) == {home.id, away.id}


def test_non_neutral_game_removes_home_field_from_strength_target(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    game = _final_game(db, home, away, kickoff, 31, 21, neutral=False, observed_at=kickoff + timedelta(hours=6))
    home_field_ratings = calculate_team_ratings(db, kickoff + timedelta(days=1), 2025)
    game.neutral_site = True
    neutral_ratings = calculate_team_ratings(db, kickoff + timedelta(days=1), 2025)

    assert (
        home_field_ratings[home.id].rating - home_field_ratings[away.id].rating
        < neutral_ratings[home.id].rating - neutral_ratings[away.id].rating
    )


def test_three_team_round_robin_is_deterministic_and_zero_centered(db):
    teams = [_team(db, name) for name in ("A", "B", "C")]
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(db, teams[0], teams[1], kickoff, 30, 20, observed_at=kickoff + timedelta(hours=6))
    _final_game(db, teams[1], teams[2], kickoff + timedelta(days=7), 27, 20, observed_at=kickoff + timedelta(days=7, hours=6))
    _final_game(db, teams[0], teams[2], kickoff + timedelta(days=14), 35, 21, observed_at=kickoff + timedelta(days=14, hours=6))
    as_of = kickoff + timedelta(days=30)

    first = calculate_team_ratings(db, as_of, 2025)
    second = calculate_team_ratings(db, as_of, 2025)

    assert first == second
    assert first[teams[0].id].rating > first[teams[1].id].rating > first[teams[2].id].rating
    assert sum(item.rating * (item.effective_games + 4) for item in first.values()) == pytest.approx(0)


def test_prior_shrinkage_and_sparse_uncertainty(db):
    teams = [_team(db, name) for name in ("A", "B", "C")]
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(db, teams[0], teams[1], kickoff, 40, 10, observed_at=kickoff + timedelta(hours=6))
    _final_game(db, teams[0], teams[1], kickoff + timedelta(days=7), 10, 20, observed_at=kickoff + timedelta(days=7, hours=6))
    _final_game(db, teams[0], teams[2], kickoff + timedelta(days=14), 24, 20, observed_at=kickoff + timedelta(days=14, hours=6))
    as_of = kickoff + timedelta(days=30)

    no_prior = calculate_team_ratings(db, as_of, 2025)
    with_prior = calculate_team_ratings(db, as_of, 2025, {teams[2].id: 20.0})

    assert with_prior[teams[2].id].rating > no_prior[teams[2].id].rating
    assert no_prior[teams[2].id].uncertainty > no_prior[teams[0].id].uncertainty
    assert with_prior[teams[2].id].uncertainty < no_prior[teams[2].id].uncertainty


def test_frozen_2025_prior_prevents_2026_future_result_leakage(db):
    teams = [_team(db, name) for name in ("A", "B", "C")]
    prior_start = datetime(2025, 9, 1, 12, tzinfo=UTC)
    first_prior_game = _final_game(
        db,
        teams[0],
        teams[1],
        prior_start,
        35,
        14,
        observed_at=prior_start + timedelta(hours=6),
    )
    _final_game(
        db,
        teams[1],
        teams[2],
        prior_start + timedelta(days=7),
        28,
        21,
        observed_at=prior_start + timedelta(days=7, hours=6),
    )
    prior_cutoff = prior_start + timedelta(days=8)
    frozen_prior = {
        team_id: rating.rating
        for team_id, rating in calculate_team_ratings(
            db,
            prior_cutoff,
            2025,
        ).items()
    }

    game_a = datetime(2026, 8, 29, 12, tzinfo=UTC)
    game_b = game_a + timedelta(days=7)
    _final_game(
        db,
        teams[0],
        teams[1],
        game_a,
        24,
        17,
        observed_at=game_a + timedelta(hours=6),
        season=2026,
    )
    before_game_b = calculate_team_ratings(db, game_b, 2026, frozen_prior)
    frozen_prior_copy = dict(frozen_prior)

    _final_game(
        db,
        teams[1],
        teams[0],
        game_b,
        45,
        10,
        observed_at=game_b + timedelta(hours=6),
        season=2026,
    )
    db.add(
        GameResultObservation(
            game_id=first_prior_game.id,
            provider="cfbd",
            home_score=0,
            away_score=70,
            status="final",
            observed_at=(game_b + timedelta(hours=12)).replace(tzinfo=None),
        )
    )
    db.flush()

    repeated_at_game_b = calculate_team_ratings(db, game_b, 2026, frozen_prior)
    after_game_b = calculate_team_ratings(
        db,
        game_b + timedelta(days=1),
        2026,
        frozen_prior,
    )

    assert frozen_prior == frozen_prior_copy
    assert repeated_at_game_b == before_game_b
    assert {rating.games_used for rating in before_game_b.values()} == {1}
    assert {rating.games_used for rating in after_game_b.values()} == {2}
    assert after_game_b != before_game_b


def test_as_of_observation_gate_prevents_future_leakage(db):
    teams = [_team(db, name) for name in ("A", "B", "C")]
    game_a = datetime(2025, 9, 1, 12, tzinfo=UTC)
    game_b = datetime(2025, 9, 8, 12, tzinfo=UTC)
    _final_game(db, teams[0], teams[1], game_a, 28, 14, observed_at=datetime(2025, 9, 1, 18, tzinfo=UTC))
    as_of_early = datetime(2025, 9, 5, tzinfo=UTC)
    before_future_exists = calculate_team_ratings(db, as_of_early, 2025)
    _final_game(db, teams[2], teams[0], game_b, 50, 0, observed_at=datetime(2025, 9, 8, 18, tzinfo=UTC))

    assert calculate_team_ratings(db, as_of_early, 2025) == before_future_exists
    assert teams[2].id not in before_future_exists
    assert teams[2].id in calculate_team_ratings(db, datetime(2025, 9, 9, tzinfo=UTC), 2025)


def test_multiple_observations_make_one_game_eligible_at_first_valid_cutoff(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    kickoff = datetime(2025, 9, 1, 12, tzinfo=UTC)
    game = _final_game(db, home, away, kickoff, 28, 14, observed_at=kickoff + timedelta(hours=6))
    db.add(
        GameResultObservation(
            game_id=game.id,
            provider="cfbd",
            home_score=14,
            away_score=28,
            status="final",
            observed_at=(kickoff + timedelta(hours=12)).replace(tzinfo=None),
        )
    )
    db.flush()

    result = calculate_rating_result(db, kickoff + timedelta(hours=7), 2025)
    revised = calculate_rating_result(db, kickoff + timedelta(hours=13), 2025)

    assert len(result.eligible_games) == 1
    assert result.eligible_games[0].home_score == 28
    assert result.eligible_games[0].away_score == 14
    assert result.eligible_games[0].observation_observed_at == kickoff + timedelta(hours=6)
    assert {rating.games_used for rating in result.ratings.values()} == {1}
    assert revised.eligible_games[0].home_score == 14
    assert revised.eligible_games[0].away_score == 28
    assert revised.eligible_games[0].observation_observed_at == kickoff + timedelta(hours=12)


def test_game_requires_observation_and_known_neutral_site(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(db, home, away, kickoff, 21, 14, neutral=None)

    assert calculate_team_ratings(db, kickoff + timedelta(days=1), 2025) == {}


def test_disconnected_components_are_deterministic(db):
    teams = [_team(db, name) for name in ("A", "B", "C", "D")]
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(db, teams[0], teams[1], kickoff, 28, 14, observed_at=kickoff + timedelta(hours=6))
    _final_game(db, teams[2], teams[3], kickoff, 21, 20, observed_at=kickoff + timedelta(hours=6))
    as_of = kickoff + timedelta(days=1)

    first = calculate_team_ratings(db, as_of, 2025)
    second = calculate_team_ratings(db, as_of, 2025)

    assert first == second
    assert set(first) == {team.id for team in teams}
    assert sum(item.rating * (item.effective_games + 4) for item in first.values()) == pytest.approx(0)


def test_market_and_npi_data_cannot_change_ratings(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    game = _final_game(db, home, away, kickoff, 31, 20, observed_at=kickoff + timedelta(hours=6))
    as_of = kickoff + timedelta(days=1)
    baseline = calculate_team_ratings(db, as_of, 2025)

    odds = Odds(game_id=game.id, sportsbook="Book", spread_home=999, spread_away=-999, moneyline_home=9999, moneyline_away=-9999, total=999)
    db.add(odds)
    db.flush()
    db.add(Prediction(game_id=game.id, model_version="NPI-4.0", market="spread", selection="away", npi_score=-999, odds_snapshot_id=odds.id))
    db.add(NikScore(game_id=game.id, model_version="NPI-4.0", recommendation="away", confidence=1))
    db.flush()

    assert calculate_team_ratings(db, as_of, 2025) == baseline
    db.query(Odds).delete()
    assert calculate_team_ratings(db, as_of, 2025) == baseline


def test_rating_result_exposes_diagnostic_and_model_identity(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    kickoff = datetime(2025, 9, 1, tzinfo=UTC)
    _final_game(db, home, away, kickoff, 24, 21, observed_at=kickoff + timedelta(hours=6))

    result = calculate_rating_result(db, kickoff + timedelta(days=1), 2025)

    assert len(result.eligible_games) == 1
    assert result.residual_rmse >= 0
    assert {rating.model_version for rating in result.ratings.values()} == {MODEL_VERSION}
    assert isinstance(next(iter(result.ratings.values())), TeamPowerRating)