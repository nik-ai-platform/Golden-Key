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
from app.services.ncaaf_power_walk_forward import (
    BOTH_RATED,
    build_walk_forward_report,
    generate_walk_forward_predictions,
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


def _game(db, home, away, kickoff, home_score, away_score):
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2025,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        home_score=home_score,
        away_score=away_score,
        status="final",
        neutral_site=False,
    )
    db.add(game)
    db.flush()
    db.add(
        GameResultObservation(
            game_id=game.id,
            provider="cfbd",
            home_score=home_score,
            away_score=away_score,
            status="final",
            observed_at=(kickoff + timedelta(hours=6)).replace(tzinfo=None),
        )
    )
    db.flush()
    return game


@pytest.fixture()
def scenario(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    start = datetime(2025, 9, 1, 12, tzinfo=UTC)
    training = _game(db, home, away, start, 28, 14)
    target = _game(db, away, home, start + timedelta(days=7), 21, 24)
    future = _game(db, home, away, start + timedelta(days=14), 35, 10)
    return home, away, training, target, future


def _prediction(db, game_id):
    return next(row for row in generate_walk_forward_predictions(db, 2025) if row.game_id == game_id)


def test_changing_future_score_does_not_change_earlier_prediction(db, scenario):
    *_, target, future = scenario
    before = _prediction(db, target.id).predicted_home_margin
    future.home_score = 100
    future.away_score = 0
    db.flush()
    assert _prediction(db, target.id).predicted_home_margin == before


def test_adding_future_game_does_not_change_earlier_prediction(db, scenario):
    home, away, _, target, future = scenario
    before = _prediction(db, target.id).predicted_home_margin
    _game(db, away, home, future.game_date.replace(tzinfo=UTC) + timedelta(days=7), 50, 0)
    assert _prediction(db, target.id).predicted_home_margin == before


def test_future_odds_do_not_change_power_prediction(db, scenario):
    *_, target, future = scenario
    before = _prediction(db, target.id).predicted_home_margin
    db.add(Odds(game_id=future.id, sportsbook="Book", spread_home=-99, spread_away=99, total=999))
    db.flush()
    assert _prediction(db, target.id).predicted_home_margin == before


def test_npi_and_prediction_rows_do_not_change_power_prediction(db, scenario):
    *_, target, _ = scenario
    before = _prediction(db, target.id).predicted_home_margin
    odds = Odds(game_id=target.id, sportsbook="Book", spread_home=-99, spread_away=99, total=999)
    db.add(odds)
    db.flush()
    db.add(Prediction(game_id=target.id, model_version="NPI-4.0", market="spread", selection="home", npi_score=999, odds_snapshot_id=odds.id))
    db.add(NikScore(game_id=target.id, final_npi=999, model_version="NPI-4.0"))
    db.flush()
    assert _prediction(db, target.id).predicted_home_margin == before


def test_target_final_score_does_not_affect_its_pregame_prediction(db, scenario):
    *_, target, _ = scenario
    before = _prediction(db, target.id).predicted_home_margin
    target.home_score = 100
    target.away_score = 0
    db.flush()
    after = _prediction(db, target.id)
    assert after.predicted_home_margin == before
    assert after.actual_home_margin == 100


def test_repeated_runs_are_identical(db, scenario):
    first = generate_walk_forward_predictions(db, 2025)
    second = generate_walk_forward_predictions(db, 2025)
    assert first == second


def test_report_covers_cold_start_metrics_and_baseline(db, scenario):
    report = build_walk_forward_report(db, 2025)
    assert report["coverage"]["total_games"] == 3
    assert report["coverage"][BOTH_RATED] == 2
    assert report["primary"]["n"] == 2
    assert report["minimum_evidence"]["1"]["n"] == 2
    assert report["naive_baseline"]["model"]["n"] == 2
    assert report["naive_baseline"]["naive_hfa"]["correlation"] is None


def test_market_benchmark_uses_latest_spread_available_before_kickoff(db, scenario):
    *_, target, _ = scenario
    before = Odds(
        game_id=target.id,
        sportsbook="Early",
        spread_home=-3.5,
        created_at=target.game_date - timedelta(hours=1),
    )
    after = Odds(
        game_id=target.id,
        sportsbook="Late",
        spread_home=-99,
        created_at=target.game_date + timedelta(hours=1),
    )
    db.add_all((before, after))
    db.flush()

    prediction = _prediction(db, target.id)

    assert prediction.market_expected_home_margin == 3.5