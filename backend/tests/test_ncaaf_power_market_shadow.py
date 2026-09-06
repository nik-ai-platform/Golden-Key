from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.ncaaf_power_market_shadow import (
    PRICE_SOURCE,
    build_shadow_report,
    build_shadow_universe,
    get_latest_pregame_market,
)
from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.nik_score import NikScore
from app.models.npi_factor_result import NPIFactorResult
from app.models.odds import Odds
from app.models.prediction_power_snapshot import PredictionPowerSnapshot
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.team_power_rating import TeamPowerRatingRecord


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


def test_latest_pregame_market_excludes_post_kickoff_odds(db):
    home = Team(name="Home", sport="NCAAF", league="NCAAF")
    away = Team(name="Away", sport="NCAAF", league="NCAAF")
    db.add_all((home, away))
    db.flush()
    kickoff = datetime(2026, 9, 5, 16, tzinfo=UTC)
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2026,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        status="scheduled",
        neutral_site=False,
    )
    db.add(game)
    db.flush()
    eligible = Odds(
        game_id=game.id,
        sportsbook="Pregame",
        spread_home=-7.0,
        spread_away=7.0,
        created_at=(kickoff - timedelta(minutes=1)).replace(tzinfo=None),
    )
    post_kickoff = Odds(
        game_id=game.id,
        sportsbook="Postgame",
        spread_home=30.0,
        spread_away=-30.0,
        created_at=(kickoff + timedelta(minutes=1)).replace(tzinfo=None),
    )
    db.add_all((eligible, post_kickoff))
    db.flush()

    market = get_latest_pregame_market(db, game.id, kickoff)

    assert market is not None
    assert market.odds_snapshot_id == eligible.id
    assert market.spread_home == -7.0
    assert market.odds_created_at < kickoff


def _add_game(
    db,
    home,
    away,
    kickoff,
    *,
    status="scheduled",
    neutral=False,
    home_score=None,
    away_score=None,
):
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2026,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        status=status,
        neutral_site=neutral,
        home_score=home_score,
        away_score=away_score,
    )
    db.add(game)
    db.flush()
    return game


def _add_observation(db, game, observed_at, home_score, away_score):
    observation = GameResultObservation(
        game_id=game.id,
        provider="cfbd",
        home_score=home_score,
        away_score=away_score,
        status="final",
        observed_at=observed_at.replace(tzinfo=None),
    )
    db.add(observation)
    db.flush()
    return observation


def _shadow_scenario(db):
    home = Team(name="Shadow Home", sport="NCAAF", league="NCAAF")
    away = Team(name="Shadow Away", sport="NCAAF", league="NCAAF")
    third = Team(name="Shadow Third", sport="NCAAF", league="NCAAF")
    db.add_all((home, away, third))
    db.flush()
    start = datetime(2026, 8, 20, 16, tzinfo=UTC)
    history = _add_game(
        db,
        home,
        away,
        start,
        status="final",
        neutral=True,
        home_score=28,
        away_score=14,
    )
    _add_observation(db, history, start + timedelta(hours=6), 28, 14)
    kickoff = start + timedelta(days=7)
    target = _add_game(
        db,
        home,
        away,
        kickoff,
        status="final",
        home_score=24,
        away_score=21,
    )
    _add_observation(db, target, kickoff + timedelta(hours=6), 24, 21)
    pregame = Odds(
        game_id=target.id,
        sportsbook="Frozen",
        spread_home=7.0,
        spread_away=-7.0,
        created_at=(kickoff - timedelta(hours=1)).replace(tzinfo=None),
    )
    db.add(pregame)
    db.flush()
    future_kickoff = kickoff + timedelta(days=7)
    future = _add_game(
        db,
        home,
        third,
        future_kickoff,
        status="final",
        neutral=True,
        home_score=70,
        away_score=0,
    )
    future_observation = _add_observation(
        db,
        future,
        future_kickoff + timedelta(hours=6),
        70,
        0,
    )
    return home, away, target, pregame, future, future_observation


def _target_row(db, target_id, prior):
    universe = build_shadow_universe(
        db,
        prior_ratings=prior,
        prior_rating_as_of=datetime(2025, 12, 31, tzinfo=UTC),
        audit_as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    return universe, next(row for row in universe.rows if row.game_id == target_id)


def test_shadow_rows_are_leakage_safe_and_do_not_persist(db):
    home, away, target, _, future, future_observation = _shadow_scenario(db)
    prior = {home.id: 5.0, away.id: -5.0}
    ratings_before = db.query(TeamPowerRatingRecord).count()
    snapshots_before = db.query(PredictionPowerSnapshot).count()
    universe, baseline = _target_row(db, target.id, prior)

    assert baseline.odds_created_at < baseline.kickoff
    assert target.id not in baseline.training_game_ids
    assert all(observed_at <= baseline.kickoff for observed_at in baseline.training_observed_ats)
    assert universe.settled_eligible_rows == 1

    future.home_score = 0
    future.away_score = 70
    future_observation.home_score = 0
    future_observation.away_score = 70
    post_kickoff_odds = Odds(
        game_id=target.id,
        sportsbook="Current",
        spread_home=-40.0,
        spread_away=40.0,
        created_at=(baseline.kickoff + timedelta(hours=1)).replace(tzinfo=None),
    )
    prediction = Prediction(
        game_id=target.id,
        model_version="NPI-4.0",
        market="spread",
        selection="AWAY",
        line_value=40.0,
        american_odds=-110,
        npi_score=-999.0,
        win_probability=0.99,
        confidence_score=0.99,
        projected_edge=0.49,
        created_at=(baseline.kickoff + timedelta(minutes=1)).replace(tzinfo=None),
    )
    db.add_all((post_kickoff_odds, prediction))
    db.flush()
    db.add_all(
        (
            PredictionResult(
                prediction_id=prediction.id,
                actual_result="HOME",
                predicted_result="AWAY",
                outcome="LOSS",
            ),
            NikScore(
                game_id=target.id,
                final_npi=-999.0,
                model_version="NPI-4.0",
                created_at=baseline.kickoff.replace(tzinfo=None),
            ),
            NPIFactorResult(
                prediction_id=prediction.id,
                factor_name="market",
                weight=999.0,
                factor_score=-999.0,
                predicted_side="AWAY",
            ),
        )
    )
    db.flush()

    _, repeated = _target_row(db, target.id, prior)

    assert repeated == baseline
    assert db.query(TeamPowerRatingRecord).count() == ratings_before
    assert db.query(PredictionPowerSnapshot).count() == snapshots_before


def test_shadow_report_uses_clamped_probabilities_and_separate_npi_join(db):
    home, away, target, pregame, _, _ = _shadow_scenario(db)
    prediction = Prediction(
        game_id=target.id,
        model_version="NPI-4.0",
        market="spread",
        selection="AWAY",
        line_value=21.5,
        american_odds=-110,
        odds_snapshot_id=pregame.id,
        npi_score=-50.0,
        win_probability=0.99,
        confidence_score=0.95,
        projected_edge=-0.50,
        created_at=(target.game_date - timedelta(hours=2)),
    )
    db.add(prediction)
    db.flush()
    universe, row = _target_row(db, target.id, {home.id: 5.0, away.id: -5.0})

    report = build_shadow_report(db, universe)

    assert row.market_margin == -7.0
    assert row.disagreement == pytest.approx(
        row.independent_model_margin - row.market_margin
    )
    assert report["L_shadow_probability_distribution"]["probabilities_95_to_100"] == 0
    assert report["L_shadow_probability_distribution"]["percentiles"]["95"] <= 0.75
    assert report["M_price_aware_edge"]["price_source_counts"] == {
        PRICE_SOURCE: 1
    }
    assert report["E_npi_4_0_comparison"]["selection_counts"]["AWAY"] == 1
    assert report["E_npi_4_0_comparison"]["giant_underdog_selection_count"] == 1
    assert report["F_settled_margin_accuracy"]["n"] == 1