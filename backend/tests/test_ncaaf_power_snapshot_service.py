from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.nik_score import NikScore
from app.models.npi_factor_result import NPIFactorResult
from app.models.odds import Odds
from app.models.prediction_power_snapshot import PredictionPowerSnapshot
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.models.team_power_rating import TeamPowerRatingRecord
from app.services.ncaaf_power_rating_service import MODEL_VERSION
from app.services.ncaaf_power_snapshot_service import (
    INSUFFICIENT_HISTORY,
    RATED,
    PowerSnapshotIntegrityError,
    calculate_and_store_team_ratings,
    calculate_pregame_power_snapshot,
    create_pregame_power_snapshot,
    get_power_snapshot,
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


def _game(db, home, away, kickoff, *, neutral=False, status="scheduled"):
    game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2025,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff.replace(tzinfo=None),
        status=status,
        neutral_site=neutral,
    )
    db.add(game)
    db.flush()
    return game


def _observation(db, game, observed_at, home_score, away_score, payload_hash=None):
    game.status = "final"
    game.home_score = home_score
    game.away_score = away_score
    observation = GameResultObservation(
        game_id=game.id,
        provider="cfbd",
        home_score=home_score,
        away_score=away_score,
        status="final",
        observed_at=observed_at.replace(tzinfo=None),
        payload_hash=payload_hash,
    )
    db.add(observation)
    db.flush()
    return observation


def _rated_target(db):
    home = _team(db, "Home")
    away = _team(db, "Away")
    start = datetime(2025, 9, 1, 12, tzinfo=UTC)
    history = _game(db, home, away, start, neutral=True)
    first_observation = _observation(
        db,
        history,
        start + timedelta(hours=6),
        28,
        14,
        "original",
    )
    target = _game(db, home, away, start + timedelta(days=7), neutral=False)
    return home, away, history, target, first_observation


def test_team_rating_records_are_reused_and_conflicts_fail(db):
    _, _, _, target, _ = _rated_target(db)
    as_of = target.game_date.replace(tzinfo=UTC)

    first = calculate_and_store_team_ratings(db, season=2025, rating_as_of=as_of)
    second = calculate_and_store_team_ratings(db, season=2025, rating_as_of=as_of)

    assert first.input_hash == second.input_hash
    assert {team_id: row.id for team_id, row in first.records.items()} == {
        team_id: row.id for team_id, row in second.records.items()
    }
    assert db.query(TeamPowerRatingRecord).count() == 2

    first_record = next(iter(first.records.values()))
    first_record.rating += 1.0
    db.flush()
    with pytest.raises(PowerSnapshotIntegrityError, match="conflicts"):
        calculate_and_store_team_ratings(db, season=2025, rating_as_of=as_of)


def test_pregame_snapshot_is_idempotent_and_unique(db):
    _, _, _, target, _ = _rated_target(db)
    as_of = target.game_date.replace(tzinfo=UTC)

    first = create_pregame_power_snapshot(db, target.id)
    second = create_pregame_power_snapshot(db, target.id)

    assert first.state == RATED
    assert first.snapshot.id == second.snapshot.id
    assert first.snapshot.rating_as_of.replace(tzinfo=UTC) == as_of
    assert first.snapshot.minimum_games_used == 1
    assert first.snapshot.independent_model_margin == pytest.approx(
        first.snapshot.home_rating - first.snapshot.away_rating + 2.5
    )
    assert get_power_snapshot(db, target.id, as_of).id == first.snapshot.id
    assert db.query(PredictionPowerSnapshot).count() == 1

    duplicate = PredictionPowerSnapshot(
        **{
            column.name: getattr(first.snapshot, column.name)
            for column in PredictionPowerSnapshot.__table__.columns
            if column.name not in {"id", "created_at"}
        }
    )
    duplicate.independent_model_margin += 1.0
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.flush()


def test_score_correction_does_not_change_earlier_snapshot_or_hash(db):
    _, _, history, target, first_observation = _rated_target(db)
    rating_as_of = first_observation.observed_at.replace(tzinfo=UTC) + timedelta(hours=1)

    first = create_pregame_power_snapshot(db, target.id, rating_as_of=rating_as_of)
    original = (
        first.snapshot.home_rating,
        first.snapshot.away_rating,
        first.snapshot.independent_model_margin,
        first.snapshot.input_hash,
    )
    correction_time = rating_as_of + timedelta(hours=1)
    _observation(db, history, correction_time, 7, 35, "corrected")

    repeated = create_pregame_power_snapshot(db, target.id, rating_as_of=rating_as_of)

    assert repeated.snapshot.id == first.snapshot.id
    assert (
        repeated.snapshot.home_rating,
        repeated.snapshot.away_rating,
        repeated.snapshot.independent_model_margin,
        repeated.snapshot.input_hash,
    ) == original
    assert repeated.snapshot.source_max_observed_at.replace(tzinfo=UTC) == (
        first_observation.observed_at.replace(tzinfo=UTC)
    )


def test_future_observation_cannot_change_snapshot(db):
    home, away, _, target, _ = _rated_target(db)
    third = _team(db, "Third")
    rating_as_of = target.game_date.replace(tzinfo=UTC)
    future_observed_game = _game(
        db,
        home,
        third,
        rating_as_of - timedelta(days=1),
        neutral=True,
    )
    future_observation = _observation(
        db,
        future_observed_game,
        rating_as_of + timedelta(hours=1),
        70,
        0,
        "future",
    )

    first = create_pregame_power_snapshot(db, target.id, rating_as_of=rating_as_of)
    values = (
        first.snapshot.home_rating,
        first.snapshot.away_rating,
        first.snapshot.independent_model_margin,
        first.snapshot.input_hash,
    )
    future_observation.home_score = 0
    future_observation.away_score = 70
    future_observed_game.home_score = 0
    future_observed_game.away_score = 70
    db.flush()

    second = create_pregame_power_snapshot(db, target.id, rating_as_of=rating_as_of)
    assert (
        second.snapshot.home_rating,
        second.snapshot.away_rating,
        second.snapshot.independent_model_margin,
        second.snapshot.input_hash,
    ) == values


def test_market_and_npi_changes_do_not_change_power_snapshot(db):
    _, _, _, target, _ = _rated_target(db)
    first = create_pregame_power_snapshot(db, target.id)
    values = (
        first.snapshot.home_rating,
        first.snapshot.away_rating,
        first.snapshot.independent_model_margin,
        first.snapshot.input_hash,
    )

    odds = Odds(
        game_id=target.id,
        sportsbook="Extreme Book",
        spread_home=999,
        spread_away=-999,
        moneyline_home=9999,
        moneyline_away=-9999,
        total=999,
    )
    db.add(odds)
    db.flush()
    prediction = Prediction(
        game_id=target.id,
        model_version="NPI-4.0",
        market="spread",
        selection="away",
        odds_snapshot_id=odds.id,
        npi_score=-999,
    )
    db.add(prediction)
    db.flush()
    db.add_all(
        [
            NikScore(
                game_id=target.id,
                model_version="NPI-4.0",
                recommendation="away",
                final_npi=-999,
                confidence=1,
            ),
            NPIFactorResult(
                prediction_id=prediction.id,
                factor_name="market",
                weight=999,
                factor_score=-999,
            ),
        ]
    )
    db.flush()

    second = create_pregame_power_snapshot(db, target.id)
    assert (
        second.snapshot.home_rating,
        second.snapshot.away_rating,
        second.snapshot.independent_model_margin,
        second.snapshot.input_hash,
    ) == values


def test_cold_start_returns_explicit_state_without_snapshot(db):
    home = _team(db, "Home")
    opponent = _team(db, "Opponent")
    unplayed = _team(db, "Unplayed")
    kickoff = datetime(2025, 9, 1, 12, tzinfo=UTC)
    history = _game(db, home, opponent, kickoff, neutral=True)
    _observation(db, history, kickoff + timedelta(hours=6), 21, 14)
    target = _game(db, home, unplayed, kickoff + timedelta(days=7))

    calculated = calculate_pregame_power_snapshot(db, target.id)
    result = create_pregame_power_snapshot(db, target.id)

    assert calculated.state == INSUFFICIENT_HISTORY
    assert calculated.independent_model_margin is None
    assert result.state == INSUFFICIENT_HISTORY
    assert result.snapshot is None
    assert result.missing_team_ids == (unplayed.id,)
    assert db.query(PredictionPowerSnapshot).count() == 0
    assert db.query(TeamPowerRatingRecord).count() == 0


def test_snapshot_rejects_post_kickoff_rating_time(db):
    _, _, _, target, _ = _rated_target(db)
    kickoff = target.game_date.replace(tzinfo=UTC)

    with pytest.raises(ValueError, match="must not be later"):
        create_pregame_power_snapshot(
            db,
            target.id,
            rating_as_of=kickoff + timedelta(seconds=1),
        )

    assert db.query(PredictionPowerSnapshot).count() == 0
    assert db.query(TeamPowerRatingRecord).count() == 0
    assert MODEL_VERSION == "NCAAF-POWER-1.0"